"""
Defines the cached, process-scoped engine and session maker singletons that
provide database connection

Every connection is tuned for faast read-only access through `sqlite3` PRAGMAs

info: Read-Only
    The database is opened in read-only mode (sqlite3's `PRAGMA query_only=ON`)
    , since the package never writes to it at runtime

info: Pre-Requisite
    - The compiled database is a prerequisite, not a dependency

    - It is built or pulled into the per-user cache directory by the
      [`Build Pipeline`][kotobase.db.builder] and only queried here

    - Until it exists, every query fails with a
      [`DatabaseNotFoundError`][kotobase.exceptions.DatabaseNotFoundError]
      that points the caller at the build or pull [`CLI`][kotobase.cli]
      commands
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from ..exceptions import DatabaseNotFoundError
from .builder import config


def _require_database() -> Path:
    """
    Returns the database path, ensuring the file is present

    Returns:
        The path of the compiled database in the cache directory

    Raises:
        DatabaseNotFoundError: If the database file does not exist
    """
    database = config.db_path()
    if not database.is_file():
        raise DatabaseNotFoundError(
            "Couldn't Find The Kotobase Database File. Please Run "
            "`kotobase build` To Build It Locally Or `kotobase pull-db` "
            "To Download The Latest Pre-Built One"
        )
    return database


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """
    Returns the process-scoped, read-only `SQLAlchemy` Engine object

    info: PRAGMAs Applied To Every Pooled Connection
        - `query_only=ON` &rarr; Reject any write on the connection,
          since the package only reads the prebuilt database, which also
          makes lending a connection across threads safe

        - `mmap_size=268435456` &rarr; Memory map up to 256 MB of the
          file so hot pages are read from the mapping instead of a `read`
          syscall and an extra copy on every access

        - `cache_size=-64000` &rarr; Keep about 64 MB of pages cached per
          connection, where the minus sign sets the size in KiB rather
          than in page count

        - `temp_store=MEMORY` &rarr; Hold the temporary b-trees used for
          sorts such as `ORDER BY` in memory rather than spilling them to
          a temp file

    Returns:
        An engine bound to the cached database with read-only PRAGMAs applied
            to every connection

    Raises:
        DatabaseNotFoundError: If the database file does not exist
    """
    database = _require_database()
    # check_same_thread=False lets the connection pool hand a connection to a
    # different thread than the one that created it. This is safe here because
    # the database is opened read-only and the pool only ever lends a given
    # connection to one thread at a time
    engine = create_engine(
        f"sqlite:///{database}",
        connect_args={"check_same_thread": False},
    )

    # Set PRAGMAs
    @event.listens_for(engine, "connect")
    def _set_pragmas(dbapi_connection: Any, _record: Any) -> None:
        """
        Attach the optional audio pack and apply read-only, read-tuned
        PRAGMAs to every pooled connection as it is opened

        Args:
            dbapi_connection (Any): The raw DBAPI connection being opened
            _record (Any): The pool's connection record, unused
        """
        cursor = dbapi_connection.cursor()
        # Attach the optional audio pack before going read only, so the `audio`
        # table resolves to it. The core database has no `audio` table of its
        # own, so an unqualified reference finds the attached pack
        pack = config.audio_db_path()
        if pack.exists():
            cursor.execute("ATTACH DATABASE ? AS audio_pack", (str(pack),))
        cursor.execute("PRAGMA query_only=ON")
        cursor.execute("PRAGMA mmap_size=268435456")
        cursor.execute("PRAGMA cache_size=-64000")
        cursor.execute("PRAGMA temp_store=MEMORY")
        cursor.close()

    return engine


@lru_cache(maxsize=1)
def get_sessionmaker() -> sessionmaker[Session]:
    """
    Returns the process-scoped session factory

    Returns:
        A session factory bound to the read only engine (also process-scoped)
    """
    return sessionmaker(
        bind=get_engine(),
        expire_on_commit=False,
        autoflush=False,
    )


@contextmanager
def session_scope() -> Iterator[Session]:
    """
    Provide a read-only session as a context manager

    Yields:
        A session that is closed when the context exits

    Raises:
        DatabaseNotFoundError: If the database file does not exist
    """
    session = get_sessionmaker()()
    try:
        yield session
    finally:
        session.close()
