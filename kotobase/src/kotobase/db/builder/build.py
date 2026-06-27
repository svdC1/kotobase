"""
Defines the builder that compiles upstream sources into one `SQLite` database

abstract: `Builder` and `Loader`
    - [`Builder`][kotobase.db.builder.build.Builder] is a coordinator with a
      single purpose, turning a stream of
      [`DatabaseRow`][kotobase.db.builder.extractors.DatabaseRow] pairs into
      one finished database. It owns the connection, the build PRAGMAs, the
      loader and the post load steps, and it delegates parsing to
      [`extractors`][kotobase.db.builder.extractors], source paths to
      [`config`][kotobase.db.builder.config] and downloading to
      [`download`][kotobase.db.builder.download]

    - [`Loader`][kotobase.db.builder.build.Loader] is the batched insert
      engine. It is kept as a separate collaborator so the builder reads as a
      recipe and the `executemany` buffering stays in one place

info: The Recipe
    - [`build_core`][kotobase.db.builder.build.build_core] Runs
      `Download` -> `Create Schema` -> `Load` -> `Build Index` ->
      `Write Metadata` -> `Optimize`

    - The read model schema is created from the `SQLAlchemy` metadata, while
      the bulk load runs on a raw `sqlite3` connection for speed
"""

from __future__ import annotations

import datetime as dt
import sqlite3
import time
from pathlib import Path
from typing import Any

import zstandard
from sqlalchemy import create_engine

from ...terminal_output import (
    THEMED_CONSOLE,
    build_status,
    inserted_rows_table,
)
from ..models import SCHEMA_VERSION, Base
from . import config
from .download import download_all
from .extractors import EXTRACTORS

_BATCH = 5000
"""
Number of rows buffered per table before they are flushed
(inserted into the database) with a single `executemany` call
"""

CORE_SOURCES = (
    "jmdict",
    "jmnedict",
    "kanjidic2",
    "kradzip",
    "kanjivg",
    "jmdict_furigana",
    "tatoeba_jpn",
)
"""
All `Source` keys downloaded for every core build, see
[`SOURCES`][kotobase.db.builder.config.SOURCES]
"""

LINK_SOURCES = ("tatoeba_links", "tatoeba_eng")
"""
Extra source keys downloaded only when `Tatoeba` sentence alignment is
requested
"""

AUDIO_SOURCES = ("kanjialive", "kanjialive_data")
"""
Extra source keys downloaded to build the optional audio pack database
"""


class Loader:
    """
    Batched multi-table insert helper for a `sqlite3` connection

    info: How It Works
        - Rows are buffered per table and flushed with `executemany` once a
          batch fills, which is far faster than inserting one row at a time

        - The insert statement for a table is derived from the keys of its
          first row, so every row for a table must carry the same keys

    Attributes:
        conn (sqlite3.Connection): The open database connection
        batch (int): Number of rows to buffer before a flush
        counts (dict[str, int]): Mapping of table names to the number of
            rows inserted to it by the instance using `add`
        _buffers (dict[str, list[tuple[Any, ...]]]): Mappng of table names
            to their individual row buffers, each one accumulates rows
            added by `add` until their length is greater than `batch`,
            upon which they are inserted into the database with
            `executemany`
        _columns (dict[str, list[str]]): Mapping of table names to a list
            containing their column names. The order is derived from the
            `add` function's `row` argument (`list(row.keys())`) when it
            is first called on a `table` and is used to build a consistent
            insert statement for subsequent rows of that same `table`
        _statements (dict[str, str]): Mapping of table names to their
            `INSERT` SQL satement derived from `rows` and `_OR_IGNORE`
    """

    _OR_IGNORE = frozenset(
        {"tag", "furigana", "radical", "kanji_radical", "kanji_strokes"},
    )
    """
    Tables that might legitimately receive duplicate rows, for example, the
    same tag emitted by thousands of senses when parsing `JMDict` or `JMNedict`
    , and so use `INSERT OR IGNORE` to let the `primary key` contract dedupe
    them silently
    """

    def __init__(
        self,
        conn: sqlite3.Connection,
        *,
        batch: int = _BATCH,
    ) -> None:
        """
        Create a loader bound to a connection

        Args:
            conn (sqlite3.Connection): The open database connection
            batch (int): Number of rows to buffer before a flush
        """
        self.conn = conn
        self.batch = batch
        self.counts: dict[str, int] = {}
        self._buffers: dict[str, list[tuple[Any, ...]]] = {}
        self._columns: dict[str, list[str]] = {}
        self._statements: dict[str, str] = {}

    def add(self, table: str, row: dict[str, Any]) -> None:
        """
        Buffer a single row for a table and flush when the batch is full

        Args:
            table (str): Target table name
            row (dict): Row whose keys are column names
        """
        # First Time Seeing A Table
        if table not in self._columns:
            # Derive Column Names From Row Keys
            columns = list(row.keys())
            # Build Statement
            verb = (
                "INSERT OR IGNORE INTO"
                if table in self._OR_IGNORE
                else "INSERT INTO"
            )
            placeholders = ", ".join(["?"] * len(columns))
            # Remember Columns + Statement For This Row Shape
            self._columns[table] = columns
            self._statements[table] = (
                f"{verb} {table} ({', '.join(columns)}) "
                f"VALUES ({placeholders})"
            )
            # Create The Table's Buffer
            self._buffers[table] = []

        # Add New Row
        self._buffers[table].append(
            tuple(row[column] for column in self._columns[table])
        )
        # Insert Filled Buffer
        if len(self._buffers[table]) >= self.batch:
            self._flush(table)

    def _flush(self, table: str) -> None:
        """
        Flush (insert into database) the buffered rows of a single table

        Args:
            table (str): Target table name
        """
        buffer = self._buffers.get(table)
        if buffer:
            self.conn.executemany(self._statements[table], buffer)
            # Save How Many Rows Were Added And Clear Buffer
            self.counts[table] = self.counts.get(table, 0) + len(buffer)
            buffer.clear()

    def flush_all(self) -> None:
        """
        Flush every buffered table

        Used to insert the remaining rows still in the buffer
        """
        for table in list(self._buffers):
            self._flush(table)


class Builder:
    """
    Coordinates building one `SQLite` database from a stream of database rows

    info: Scope
        The builder owns only what is intrinsic to writing the database
        efficiently, which includes the following

        - The connection

        - The build PRAGMAs

        - A [`Loader`][kotobase.db.builder.build.Loader]

        - The post load steps

        - Any arguments which the
          [`Extractors`][kotobase.db.builder.extractors] might receive

    Attributes:
        path (Path): The database file being written
        conn (sqlite3.Connection): The open connection used for the bulk load
        loader (Loader): The batched insert helper bound to the connection
    """

    _FTS_SCRIPT = """
    CREATE VIRTUAL TABLE gloss_fts USING fts5(text, sense_id UNINDEXED);
    INSERT INTO gloss_fts(rowid, text, sense_id)
        SELECT id, text, sense_id FROM jmdict_gloss;
    """
    """
    Builds the English gloss FTS5 index after the bulk load

    info: FTS5 Usage
        - Only the `JMDict` gloss index uses FTS5

        - Headword lookups hit the indexed form tables directly

        - Japanese sentence search uses `LIKE` with an early `LIMIT`, so
          dedicated headword and sentence indexes would only add size
    """

    def __init__(self, path: Path) -> None:
        """
        Open a connection to the target database and prepare it for loading

        Args:
            path (Path): The database file to write, with its schema already
                created
        """
        self.path = path
        self.conn = sqlite3.connect(path)
        self._apply_build_pragmas()
        self.loader = Loader(self.conn)

    def __enter__(self) -> Builder:
        """
        Enter the builder context

        Returns:
            The builder itself
        """
        return self

    def __exit__(self, *exc: Any) -> None:
        """
        Close the connection on exit

        Args:
            *exc (object): The 3 exception arguments, ignored
        """
        self.conn.close()

    def _apply_build_pragmas(self) -> None:
        """
        Apply fast, unsafe PRAGMAs for the duration of the bulk load

        These trade crash safety for speed, which is the right trade for a
        build because a failed build is simply rerun rather than recovered

        info: PRAGMAs
            - `journal_mode=OFF` &rarr; No rollback journal. Crash recovery
              has no value for a throwaway build, and this avoids a journal
              write on every statement

            - `synchronous=OFF` &rarr; Do not fsync. The OS may reorder or lose
              writes on a crash, but the half-built database is discarded in
              that case anyway

            - `temp_store=MEMORY` &rarr; Keep temporary b-trees,
              used while sorting and indexing, in memory

            - `cache_size=-200000` &rarr; About 200 MB of page cache so that
              the hot working set stays in RAM

            - `mmap_size=268435456` &rarr; Memory map 256 MB of the file to cut
              read syscalls during the load
        """
        self.conn.execute("PRAGMA journal_mode=OFF")
        self.conn.execute("PRAGMA synchronous=OFF")
        self.conn.execute("PRAGMA temp_store=MEMORY")
        self.conn.execute("PRAGMA cache_size=-200000")
        self.conn.execute("PRAGMA mmap_size=268435456")

    def run(self, name: str, *args: Any) -> None:
        """
        Stream one registered extractor through the loader

        The extractor is looked up by name in
        [`EXTRACTORS`][kotobase.db.builder.extractors.EXTRACTORS] and called
        with whatever positional arguments it declares, since each extractor
        owns its own signature

        Args:
            name (str): Registry key of the extractor to run
            *args (Any): Positional arguments forwarded to the extractor, such
                as the downloaded source paths it parses
        """
        for table, row in EXTRACTORS[name].run(*args):
            self.loader.add(table, row)

    def finish_load(self) -> None:
        """
        Flush the remaining buffered rows and commit the bulk load

        The streamed inserts accumulate in a single implicit transaction, so
        this commits them once at the end
        """
        self.loader.flush_all()
        self.conn.commit()

    def report_counts(self) -> None:
        """
        Print the number of rows inserted into each table
        """
        THEMED_CONSOLE.print(inserted_rows_table(self.loader.counts))

    def build_fts(self) -> None:
        """
        Create the gloss full text search index after the bulk load
        """
        self.conn.executescript(self._FTS_SCRIPT)
        self.conn.commit()

    def write_meta(self, paths: dict[str, Path], seconds: float) -> None:
        """
        Record build metadata into the `db_meta` table

        Args:
            paths (dict[str, Path]): Mapping of source key to downloaded file
            seconds (float): Wall clock build duration in seconds
        """
        size_mb = self.path.stat().st_size / 1024 / 1024
        meta = {
            "schema_version": str(SCHEMA_VERSION),
            "build_date": dt.datetime.now(dt.timezone.utc).isoformat(),
            "build_seconds": f"{seconds:.1f}",
            "size_mb": f"{size_mb:.1f}",
        }
        for key, path in paths.items():
            meta[f"source.{key}"] = Path(path).name
        self.conn.executemany(
            "INSERT OR REPLACE INTO db_meta(key, value) VALUES (?, ?)",
            list(meta.items()),
        )
        self.conn.commit()

    def optimize(self, *, analyze: bool = True) -> None:
        """
        Restore a normal journal, update statistics and compact the file

        Args:
            analyze (bool): When True, run `ANALYZE` so the query planner has
                statistics, which the small audio pack does not need
        """
        self.conn.execute("PRAGMA journal_mode=DELETE")
        if analyze:
            self.conn.execute("ANALYZE")
        self.conn.commit()
        self.conn.execute("VACUUM")


def _create_schema(
    path: Path,
    *,
    only: set[str] | None = None,
    exclude: set[str] | None = None,
) -> None:
    """
    Create the read model schema on an empty database file

    The schema is defined once in the SQLAlchemy metadata, so it is created
    through a temporary engine that is disposed immediately, leaving the bulk
    load to run on a raw sqlite3 connection

    Args:
        path (Path): The database file to create the schema in
        only (set[str] | None): When given, only these tables are created
        exclude (set[str] | None): Tables to skip, such as the audio table for
            a core build
    """
    only_set = only or set()
    exclude_set = exclude or set()
    tables = [
        table
        for table in Base.metadata.sorted_tables
        if (not only_set or table.name in only_set)
        and table.name not in exclude_set
    ]
    engine = create_engine(f"sqlite:///{path}")
    Base.metadata.create_all(engine, tables=tables)
    engine.dispose()


def build_core(
    *,
    force: bool = False,
    include_links: bool = True,
) -> Path:
    """
    Build the kotobase core database from its sources

    Args:
        force (bool): When True, rebuild even if a database already exists
        include_links (bool): When True, download and align the Tatoeba links
            and English sentences, which is the heaviest part of the build

    Returns:
        The path of the compiled database

    Raises:
        FileExistsError: If a database already exists and `force` is False
    """
    config.ensure_dirs()
    target = config.db_path()
    if target.exists() and not force:
        raise FileExistsError(
            f"Database Already Exists At '{target}', Pass Force To Rebuild"
        )

    keys = list(CORE_SOURCES)
    if include_links:
        keys += list(LINK_SOURCES)

    with build_status("[heading]Downloading Sources[/]"):
        paths = download_all(keys)
    with build_status("[heading]Creating Schema[/]"):
        target.unlink(missing_ok=True)
        # Audio lives in the separate pack, not the core database
        _create_schema(target, exclude={"audio"})

    # Tatoeba alignment is optional, so its link and English sources are passed
    # only when they were downloaded. Each plan entry pairs an extractor name
    # with the arguments that extractor declares
    links = paths.get("tatoeba_links") if include_links else None
    english = paths.get("tatoeba_eng") if include_links else None
    plan: list[tuple[str, tuple[Any, ...]]] = [
        ("jmdict", (paths["jmdict"],)),
        ("jmnedict", (paths["jmnedict"],)),
        ("kanjidic", (paths["kanjidic2"],)),
        ("krad", (paths["kradzip"],)),
        ("furigana", (paths["jmdict_furigana"],)),
        ("kanjivg", (paths["kanjivg"],)),
        ("jlpt", ()),
        ("tatoeba", (paths["tatoeba_jpn"], links, english)),
    ]

    started = time.perf_counter()
    with Builder(target) as builder:
        with build_status("[heading]Loading Data[/]") as status:
            for name, source_args in plan:
                status.update(f"[heading]Loading Data[/] [muted]({name})[/]")
                builder.run(name, *source_args)
            status.update("[info]Finalizing[/]")
            builder.finish_load()
        builder.report_counts()

        with build_status("[heading]Building Search Index[/]"):
            builder.build_fts()
        builder.write_meta(paths, time.perf_counter() - started)

        with build_status("[heading]Optimizing[/]"):
            builder.optimize()

    elapsed = time.perf_counter() - started
    size_mb = target.stat().st_size / 1024 / 1024
    THEMED_CONSOLE.print(
        f"[bold_success]Built[/] [info]{target}[/] [muted] "
        f"({size_mb:.1f} MB)[/] [bold_success]In[/]"
        f" {elapsed:.1f}s"
    )
    return target


def build_audio(*, force: bool = False) -> Path:
    """
    Build the optional audio pack from the Kanji alive media

    The audio pack is a separate database holding only the `audio` table, which
    the read layer attaches when it is present. Keeping it out of the core
    database keeps the default download small

    Args:
        force (bool): When True, rebuild even if the pack already exists

    Returns:
        The path of the compiled audio pack

    Raises:
        FileExistsError: If the pack already exists and `force` is False
    """
    config.ensure_dirs()
    pack = config.audio_db_path()
    if pack.exists() and not force:
        raise FileExistsError(
            f"Audio Pack Database Already Exists At '{pack}', Pass Force To"
            f" Rebuild"
        )

    THEMED_CONSOLE.print("[heading]Downloading Sources[/]")
    paths = download_all(list(AUDIO_SOURCES))

    with build_status("[heading]Creating Schema[/]"):
        pack.unlink(missing_ok=True)
        _create_schema(pack, only={"audio"})

    with Builder(pack) as builder:
        with build_status("[heading]Building Audio Pack[/]"):
            builder.run("audio", paths["kanjialive"], paths["kanjialive_data"])
            builder.finish_load()
        builder.report_counts()
        with build_status("[heading]Optimizing[/]"):
            builder.optimize(analyze=False)

    size_mb = pack.stat().st_size / 1024 / 1024
    THEMED_CONSOLE.print(
        f"[bold_success]Built[/] [info]{pack}[/] [muted]({size_mb:.1f} MB)[/]"
    )
    return pack


def compress(database: Path | None = None) -> Path:
    """
    Compress a built database to a zstandard archive for publishing

    Args:
        database (Path | None): Database to compress, or None for the default
            cache location

    Returns:
        The path of the written zstandard archive
    """
    source = database or config.db_path()
    destination = source.with_name(source.name + ".zst")
    compressor = zstandard.ZstdCompressor(level=19)
    with open(source, "rb") as raw, open(destination, "wb") as packed:
        compressor.copy_stream(raw, packed)
    return destination
