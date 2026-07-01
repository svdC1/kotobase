"""
Defines the Kotobase `CLI` built on `Typer` and rendered with `Rich`


info: Command Groups
    - Query commands call the [`Kotobase`][kotobase.api.Kotobase] wrapper and
      either pretty-print the result or emit machine readable JSON (`--json`)

    - Build and distribution commands defer to the
      [`Build Piepline`][kotobase.db.builder]

    - Commands to manage the package's cache directory which holds the
      database files and build artifacts
"""

from __future__ import annotations

import io
import json
import shutil
import sys
from pathlib import Path
from typing import Annotated, Any

import typer
from pydantic import BaseModel

from . import __version__
from . import terminal_output as out
from .api import Kotobase
from .db import builder
from .exceptions import (
    AudioDatabaseNotFoundError,
    DatabaseExistsError,
    DatabaseNotFoundError,
    DownloadError,
    KotobaseError,
    SourceExtractionError,
)
from .terminal_output import THEMED_CONSOLE

# --- App Definition ---

app = typer.Typer(
    name="kotobase",
    add_completion=False,
    no_args_is_help=True,
    help="Kotobase, a comprehensive Japanese language database",
)

lookup_app = typer.Typer(
    name="lookup",
    no_args_is_help=True,
    add_completion=False,
    help="Query The Kotobase Database",
)

db_app = typer.Typer(
    name="db",
    no_args_is_help=True,
    add_completion=False,
    help="Build The Kotobase Database Locally Or Pull A Pre-Built One",
)

cache_app = typer.Typer(
    name="cache",
    no_args_is_help=True,
    add_completion=False,
    help=(
        "Manage The Cache Directory In Which The Database And Build Artifacts "
        "Are Stored"
    ),
)

app.add_typer(lookup_app)
app.add_typer(db_app)
app.add_typer(cache_app)


# --- Helpers ---

KB = Kotobase()
"""
Shared [`Kotobase`][kotobase.api.Kotobase] instance which executes query
commands
"""


def _to_json(obj: Any) -> str:
    """
    Serialize a result object, or a list of them, to `JSON` text keeping
    non-ascii characters verbatim

    Args:
        obj (Any): A data transfer object, a list of them, or a plain value

    Returns:
        The object encoded as a `JSON` string
    """
    if isinstance(obj, BaseModel):
        return obj.model_dump_json()
    if isinstance(obj, list):
        return json.dumps(
            [
                item.model_dump(mode="json")
                if isinstance(item, BaseModel)
                else item
                for item in obj
            ],
            ensure_ascii=False,
        )
    return json.dumps(obj, ensure_ascii=False)


def _path_size(path: Path) -> int:
    """
    Compute the total size in bytes of a file or directory tree

    Args:
        path (Path): The file or directory to measure

    Returns:
        The total size in bytes, or 0 when the path does not exist
    """
    if path.is_dir():
        return sum(p.stat().st_size for p in path.rglob("*") if p.is_file())
    if path.is_file():
        return path.stat().st_size
    return 0


def _kanji_find_title(
    stroke: int | None,
    grade: int | None,
    skip: str | None,
    freq: int | None,
    level: int | None,
) -> str:
    """
    Build a Title Cased description of an active kanji search

    Args:
        stroke (int | None): Required stroke count
        grade (int | None): Required school grade
        skip (str | None): Required SKIP code
        freq (int | None): Maximum frequency rank
        level (int | None): Required JLPT level

    Returns:
        A description such as `Kanji · 5 Strokes · N5`
    """
    parts = ["Kanji"]
    if stroke is not None:
        parts.append(f"{stroke} Strokes")
    if grade is not None:
        parts.append(f"Grade {grade}")
    if skip is not None:
        parts.append(f"SKIP {skip}")
    if freq is not None:
        parts.append(f"Freq ≤ {freq}")
    if level is not None:
        parts.append(f"N{level}")
    return " · ".join(parts)


# --- Root Commands ---


@app.command(name="version")
def version() -> None:
    """
    Prints The Installed Kotobase Version
    """
    THEMED_CONSOLE.print(f"[heading]kotobase[/] [info]{__version__}[/]")


# --- Lookup Commands ---


@lookup_app.command(name="all")
def lookup_all(
    query: Annotated[
        str,
        typer.Argument(
            ...,
            help="Word In Kana / Kanji Or A Wildcard Pattern (-w)",
        ),
    ],
    names: Annotated[
        bool,
        typer.Option(
            "-n",
            "--names",
            help="Include Proper Name Results From JMNedict",
        ),
    ] = False,
    wildcard: Annotated[
        bool,
        typer.Option(
            "-w",
            "--wildcard",
            help="Treat * And % As Wildcards In 'query'",
        ),
    ] = False,
    sentence_limit: Annotated[
        int,
        typer.Option(
            "-sl",
            "--sentence-limit",
            help="Number Of Tatoeba Example Sentences To Show",
        ),
    ] = 5,
    labels: Annotated[
        bool,
        typer.Option(
            "-l",
            "--labels",
            help="Expand JMDict / JMNedcit Tag Codes To Their Descriptions",
        ),
    ] = False,
    as_json: Annotated[
        bool,
        typer.Option(
            "-j",
            "--json",
            help="Format The Result As JSON",
        ),
    ] = False,
) -> None:
    """
    Run A Comprehensive Database Lookup For `query` Across All Data Sources
    """
    result = KB.lookup(
        query,
        wildcard=wildcard,
        include_names=names,
        sentence_limit=sentence_limit,
        with_labels=labels,
    )
    if as_json:
        typer.echo(_to_json(result))
        return
    out.render_lookup(result, with_names=names)


@lookup_app.command(name="kanji")
def lookup_kanji(
    literal: Annotated[
        str,
        typer.Argument(
            ...,
            help="A Single Kanji Character",
        ),
    ],
    as_json: Annotated[
        bool,
        typer.Option(
            "-j",
            "--json",
            help="Format The Result As JSON",
        ),
    ] = False,
) -> None:
    """
    Display All Available Information For A Single Kanji Literal
    """
    result = KB.kanji(literal)
    if as_json:
        typer.echo(_to_json(result))
        return
    if result is None:
        out.render_no_results(literal)
        return
    out.render_kanji(result)


@lookup_app.command(name="jlpt")
def lookup_jlpt(
    word: Annotated[
        str,
        typer.Argument(
            ...,
            help="Word Or Kanji",
        ),
    ],
) -> None:
    """
    Show JLPT Levels For A Word And Its Kanji
    """
    out.render_word_jlpt(KB.lookup(word))


@lookup_app.command(name="kanji-find")
def lookup_find_kanji(
    stroke: Annotated[
        int | None,
        typer.Option(
            "-s",
            "--stroke",
            help="Required Number Of Strokes",
        ),
    ] = None,
    grade: Annotated[
        int | None,
        typer.Option(
            "-g",
            "--grade",
            help="Required School Grade In Which It's Learned",
        ),
    ] = None,
    skip: Annotated[
        str | None,
        typer.Option(
            "--skip",
            help="SKIP Code",
        ),
    ] = None,
    freq: Annotated[
        int | None,
        typer.Option(
            "-f",
            "--freq",
            help="Maximum Newspaper Frequency Rank",
        ),
    ] = None,
    level: Annotated[
        int | None,
        typer.Option(
            "--jlpt",
            help="Required JLPT Level In Tanos List",
        ),
    ] = None,
    limit: Annotated[
        int,
        typer.Option(
            "-l",
            "--limit",
            help="Maximum Number Of Results To Display",
        ),
    ] = 30,
    as_json: Annotated[
        bool,
        typer.Option(
            "-j",
            "--json",
            help="Format The Result As JSON",
        ),
    ] = False,
) -> None:
    """
    Search A Kanji By Its Stroke Count, Grade, SKIP Code, Frequency Or JLPT
    Level
    """
    if skip is not None:
        results = KB.kanji_by_skip(skip, limit=limit)
    else:
        results = KB.search_kanji(
            stroke_count=stroke,
            grade=grade,
            freq_max=freq,
            jlpt=level,
            limit=limit,
        )
    if as_json:
        typer.echo(_to_json(results))
        return
    out.render_kanji_table(
        results,
        title=_kanji_find_title(stroke, grade, skip, freq, level),
    )


@lookup_app.command(name="radicals")
def lookup_radicals(
    components: Annotated[
        list[str] | None,
        typer.Argument(
            help="Radicals To Require, Or None To List Every Radical",
        ),
    ] = None,
    as_json: Annotated[
        bool,
        typer.Option(
            "-j",
            "--json",
            help="Format Results As JSON",
        ),
    ] = False,
) -> None:
    """
    List Kanji Radicals, Or Find Kanji That Contain Every Given Radical
    """
    if components:
        matches = KB.by_radicals(components)
        if as_json:
            typer.echo(_to_json(matches))
            return
        out.render_kanji_table(matches, title="Kanji By Radicals")
        return
    radicals = KB.radicals()
    if as_json:
        typer.echo(_to_json(radicals))
        return
    out.render_radicals(radicals)


@lookup_app.command(name="jlpt-list")
def lookup_jlpt_list(
    kind: Annotated[
        str,
        typer.Argument(
            ...,
            help="One Of 'vocab', 'kanji, or 'grammar'",
        ),
    ],
    level: Annotated[
        int,
        typer.Argument(
            ...,
            help="JLPT Level From 1 To 5",
        ),
    ],
    as_json: Annotated[
        bool,
        typer.Option(
            "-j",
            "--json",
            help="Format Results As JSON",
        ),
    ] = False,
) -> None:
    """
    Show A Full Tanos JLPT Study List By Its Kind And Level
    """
    try:
        results = KB.jlpt_list(kind, level)
    except ValueError:
        THEMED_CONSOLE.print(
            "[danger]⊗ Unknown JLPT Kind -> Use[/][heading] vocab[/]"
            "[danger],[/][heading] kanji[/][danger] Or[/][heading] grammar[/]"
        )
        raise typer.Exit(1) from None
    if as_json:
        typer.echo(_to_json(results))
        return
    out.render_jlpt_list(results, kind=kind, level=level)


@lookup_app.command(name="names")
def lookup_names(
    form: Annotated[
        str | None,
        typer.Argument(
            help="A Proper Name To Search For Or None To Browse By --type",
        ),
    ] = None,
    name_type: Annotated[
        str | None,
        typer.Option(
            "-t",
            "--type",
            help="Browse A Name Type Such As 'place'",
        ),
    ] = None,
    as_json: Annotated[
        bool,
        typer.Option(
            "-j",
            "--json",
            help="Format Results As JSON",
        ),
    ] = False,
) -> None:
    """
    Look Up Or Browse JMnedict Proper Names
    """
    results = KB.names(form, name_type=name_type)
    if as_json:
        typer.echo(_to_json(results))
        return
    out.render_names(results)


@lookup_app.command(name="meaning")
def lookup_meaning(
    query: Annotated[
        str,
        typer.Argument(
            ...,
            help="English Meaning To Search For",
        ),
    ],
    limit: Annotated[
        int,
        typer.Option(
            "-l",
            "--limit",
            help="Maximum Number Of Results To Show",
        ),
    ] = 30,
    as_json: Annotated[
        bool,
        typer.Option(
            "-j",
            "--json",
            help="Emit JSON",
        ),
    ] = False,
) -> None:
    """
    Find Entries By Their English Meaning
    """
    results = KB.search_meaning(query, limit=limit)
    if as_json:
        typer.echo(_to_json(results))
        return
    out.render_entries(results, query=query)


@lookup_app.command(name="sentences")
def lookup_sentences(
    text_value: Annotated[
        str,
        typer.Argument(
            ...,
            help="Text To Search For",
        ),
    ],
    limit: Annotated[
        int,
        typer.Option(
            "--limit",
            help="Maximum Number Of Results To Display",
        ),
    ] = 10,
    as_json: Annotated[
        bool,
        typer.Option(
            "-j",
            "--json",
            help="Format Results As JSON",
        ),
    ] = False,
) -> None:
    """
    Find Japanese Example Sentences Containing A Specific Text
    """
    results = KB.sentences(text_value, limit=limit)
    if as_json:
        typer.echo(_to_json(results))
        return
    out.render_sentences(results, query=text_value)


@lookup_app.command(name="furigana")
def lookup_furigana(
    word: Annotated[
        str,
        typer.Argument(
            ...,
            help="A Written Spelling",
        ),
    ],
    as_json: Annotated[
        bool,
        typer.Option(
            "-j",
            "--json",
            help="Format The Result As JSON",
        ),
    ] = False,
) -> None:
    """
    Show Furigana Segmentation For A Written Form
    """
    results = KB.furigana(word)
    if as_json:
        typer.echo(_to_json(results))
        return
    out.render_furigana(results)


@lookup_app.command(name="kanji-svg")
def lookup_kanji_svg(
    literal: Annotated[
        str,
        typer.Argument(
            ...,
            help="A Single Kanji Character",
        ),
    ],
    raw: Annotated[
        bool,
        typer.Option(
            "--raw",
            help="Emit The Raw KanjiVG Fragment Instead Of A Renderable SVG",
        ),
    ] = False,
) -> None:
    """
    Print A Kanji's Stroke Order As A Renderable SVG Document
    """
    svg = KB.stroke_svg(literal, raw=raw)
    if svg is None:
        out.render_no_results(literal)
        return
    typer.echo(svg)


@lookup_app.command(name="audio")
def lookup_audio(
    key: Annotated[
        str,
        typer.Argument(
            ...,
            help="A Kanji Or Word",
        ),
    ],
    out_dir: Annotated[
        Path | None,
        typer.Option(
            "-o",
            "--out",
            help="Directory To Save The Audio Clips Into",
        ),
    ] = None,
    as_json: Annotated[
        bool,
        typer.Option(
            "-j",
            "--json",
            help="Format Results As JSON",
        ),
    ] = False,
) -> None:
    """
    List Or Download Pronunciation Audio For A Kanji Or Word
    """
    clips = KB.audio(key)
    if as_json:
        typer.echo(_to_json(clips))
        return
    if not clips:
        out.render_no_results(key)
        return
    if out_dir is not None:
        out.render_audio_saved(KB.save_audio(key, out_dir))
        return
    out.render_audio(key, clips)


# --- DB Commands ---


@db_app.command(name="info")
def db_info() -> None:
    """
    Show Build Metadata For The Active Database
    """
    out.render_db_info(KB.db_info())


@db_app.command(name="build")
def db_build(
    force: Annotated[
        bool,
        typer.Option(
            "-f",
            "--force",
            help="Rebuild The Database Even When It's Present",
        ),
    ] = False,
    with_links: Annotated[
        bool,
        typer.Option(
            "--with-links/--no-links",
            help=(
                "Align Tatoeba Example Sentences To Their English Translation"
            ),
        ),
    ] = True,
    with_audio: Annotated[
        bool,
        typer.Option(
            "--with-audio/--no-audio",
            help=(
                "Also Build The Optional Audio Database To Have Access To "
                "Pronunciation Clips"
            ),
        ),
    ] = True,
) -> None:
    """
    Download Upstream Sources And Build The Database Locally
    """
    builder.build_core(force=force, include_links=with_links)
    if with_audio:
        builder.build_audio(force=force)


@db_app.command(name="pull")
def db_pull(
    tag: Annotated[
        str | None,
        typer.Option(
            "-t", "--tag", help="Specify A Specific Release Tag To Pull"
        ),
    ] = None,
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            help="Replace When The Database Is Already Present",
        ),
    ] = False,
    with_audio: Annotated[
        bool,
        typer.Option(
            "--with-audio/--no-audio",
            help=(
                "Also Pull The Additional Audio Database To Have Access To "
                "Pronunciation Clips"
            ),
        ),
    ] = True,
) -> None:
    """
    Download a Pre-Built Database From A GitHub Release
    """
    builder.pull_db(tag=tag, force=force)
    if with_audio:
        builder.pull_audio(tag=tag, force=force)


# --- Cache Commands ---


@cache_app.command(name="clear")
def cache_clear(
    yes: Annotated[
        bool,
        typer.Option(
            "-y",
            "--yes",
            help="Skip Confirmation",
        ),
    ] = False,
    sources_only: Annotated[
        bool,
        typer.Option(
            "--sources-only",
            help=(
                "Delete Only The Raw Upstream Sources Downloaded During A "
                " Build"
            ),
        ),
    ] = False,
    db_only: Annotated[
        bool,
        typer.Option(
            "--db-only",
            help=(
                "Delete Only The Pulled / Built Databases, Leaving Raw "
                "Upstream Sources Downloaded During A Build"
            ),
        ),
    ] = False,
) -> None:
    """
    Delete The Entire Kotobase Cache Directory, Or Specific Items Within It
    """
    config = builder.config
    if sources_only:
        targets = [config.raw_dir()]
    elif db_only:
        targets = [config.db_path(), config.audio_db_path()]
    else:
        targets = [config.raw_dir(), config.db_path(), config.audio_db_path()]
    existing = [path for path in targets if path.exists()]
    if not existing:
        out.render_cache_cleared([], 0)
        return
    if not yes:
        typer.confirm(f"Delete {len(existing)} Cache Path(s)?", abort=True)
    freed = sum(_path_size(path) for path in existing)
    removed: list[Path] = []
    for path in existing:
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
        removed.append(path)
    out.render_cache_cleared(removed, freed)


@cache_app.command(name="path")
def cache_path() -> None:
    """
    Display The File System Path Of The Kotobase Cache Directory
    """
    out.render_cache_path(builder.config.cache_dir())


@cache_app.command(name="size")
def cache_size() -> None:
    """
    Display The Total Disk Size Occupied By The Kotobase Cache Directory
    """
    config = builder.config
    sizes = {
        "Raw Sources": _path_size(config.raw_dir()),
        "Core Database": _path_size(config.db_path()),
        "Audio Database": _path_size(config.audio_db_path()),
    }
    out.render_cache_size(sizes)


def _render_error(exc: KotobaseError) -> None:
    """
    Render a Kotobase error as a themed, user-friendly message

    Args:
        exc (KotobaseError): The error raised while running a command
    """
    if isinstance(exc, AudioDatabaseNotFoundError):
        THEMED_CONSOLE.print(
            "[danger]⊗ Couldn't Find The Audio Database -> Run [/]"
            "[heading]kotobase db pull[/][danger] Or "
            "[/][heading]kotobase db build[/]"
        )
    elif isinstance(exc, DatabaseNotFoundError):
        THEMED_CONSOLE.print(
            "[danger]⊗ Couldn't Find The Core Database -> Run [/]"
            "[heading]kotobase db pull[/][danger] Or "
            "[/][heading]kotobase db build[/]"
        )
    elif isinstance(exc, DatabaseExistsError):
        THEMED_CONSOLE.print(
            f"[danger]⊗ {exc}[/]  [muted](Use --force To Replace)[/]"
        )
    elif isinstance(exc, DownloadError):
        THEMED_CONSOLE.print(f"[danger]⊗ Download Failed -> {exc}[/]")
    elif isinstance(exc, SourceExtractionError):
        THEMED_CONSOLE.print(f"[danger]⊗ Source Processing Failed -> {exc}[/]")
    else:
        THEMED_CONSOLE.print(f"[danger]⊗ {exc}[/]")


def main() -> None:
    """
    CLI entry point

    Forces UTF-8 output and renders [`KotobaseError`][kotobase.exceptions]
    failures as friendly messages with a non-zero exit instead of tracebacks
    """
    # Force UTF-8 on stdout and stderr so Japanese text survives redirection.
    # On Windows, a redirected stream defaults to a legacy code page (cp1252)
    # that cannot encode kana or kanji, which otherwise crashes piped or `>`
    # output
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8")
    if isinstance(sys.stderr, io.TextIOWrapper):
        sys.stderr.reconfigure(encoding="utf-8")
    try:
        app()
    except KotobaseError as exc:
        _render_error(exc)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
