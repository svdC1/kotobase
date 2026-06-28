"""
Defines a registry for upstream sources and file-system constants for
kotobase's [`Build Pipeline`][kotobase.db.builder.build]

abstract: Data Storage + Acquisition
    - This module is the single source of truth for where raw data comes from
      and where build artifacts are written

    - Every upstream source is described by a
      [`Source`][kotobase.db.builder.config.Source] record in
      [`SOURCES`][kotobase.db.builder.config.SOURCES]

    - Large, regenerable artifacts like raw downloads, the compiled database
      , and the optional audio pack live in a per user cache directory
      (`platformdirs`) rather than inside the package

    - The cache location can be overridden with the
      `KOTOBASE_CACHE_DIR` environment variable

    - The only data shipped inside the wheel is the small, already-processed
      Tanos JLPT `JSON` files under `kotobase.data`
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

from platformdirs import PlatformDirs

# --- Source Registry ---


@dataclass(frozen=True, slots=True)
class Source:
    """
    Represents a single upstream data sources

    info: Acquisition
        - A source is fetched either from a direct `url` or, for projects that
          publish GitHub releases, from the latest release of `github_repo`

        - In the release case, the asset is selected by the exact `asset` name
          , or by the `asset_pattern` regular expression

    Attributes:
        key (str): Stable identifier used as the registry key and cache file
            stem
        license (str): SPDX style license identifier for the source data
        homepage (str): Canonical homepage or repository for attribution
        url (str | None): Direct download URL when the source is a plain file
        github_repo (str | None): GitHub `owner/name` when the source is a
            release asset
        asset (str | None): Exact release asset filename to download
        asset_pattern (str | None): Regular expression matching the release
            asset filename when the name carries a version or date
        optional (bool): True when the source may be skipped without failing a
            core build, for example the audio sources
    """

    key: str
    license: str
    homepage: str
    url: str | None = None
    github_repo: str | None = None
    asset: str | None = None
    asset_pattern: str | None = None
    optional: bool = False


SOURCES: dict[str, Source] = {
    "jmdict": Source(
        key="jmdict",
        license="CC-BY-SA-4.0",
        homepage="https://www.edrdg.org/edrdg/licence.html",
        url="http://ftp.edrdg.org/pub/Nihongo/JMdict_e.gz",
    ),
    "jmnedict": Source(
        key="jmnedict",
        license="CC-BY-SA-4.0",
        homepage="https://www.edrdg.org/edrdg/licence.html",
        url="http://ftp.edrdg.org/pub/Nihongo/JMnedict.xml.gz",
    ),
    "kanjidic2": Source(
        key="kanjidic2",
        license="CC-BY-SA-4.0",
        homepage="https://www.edrdg.org/edrdg/licence.html",
        url="http://www.edrdg.org/kanjidic/kanjidic2.xml.gz",
    ),
    "kradzip": Source(
        key="kradzip",
        license="CC-BY-SA-4.0",
        homepage="https://www.edrdg.org/edrdg/licence.html",
        url="http://ftp.edrdg.org/pub/Nihongo/kradzip.zip",
    ),
    "kanjivg": Source(
        key="kanjivg",
        license="CC-BY-SA-3.0",
        homepage="https://kanjivg.tagaini.net/",
        github_repo="KanjiVG/kanjivg",
        asset_pattern=r"kanjivg-\d+\.xml\.gz",
    ),
    "jmdict_furigana": Source(
        key="jmdict_furigana",
        license="CC-BY-SA-4.0",
        homepage="https://github.com/Doublevil/JmdictFurigana",
        github_repo="Doublevil/JmdictFurigana",
        asset="JmdictFurigana.json.tar.gz",
    ),
    "jmnedict_furigana": Source(
        key="jmnedict_furigana",
        license="CC-BY-SA-4.0",
        homepage="https://github.com/Doublevil/JmdictFurigana",
        github_repo="Doublevil/JmdictFurigana",
        asset="JmnedictFurigana.json.tar.gz",
        optional=True,
    ),
    "tatoeba_jpn": Source(
        key="tatoeba_jpn",
        license="CC-BY-2.0-FR",
        homepage="https://tatoeba.org/eng/terms_of_use",
        url=(
            "https://downloads.tatoeba.org/exports/per_language/jpn/"
            "jpn_sentences.tsv.bz2"
        ),
    ),
    "tatoeba_eng": Source(
        key="tatoeba_eng",
        license="CC-BY-2.0-FR",
        homepage="https://tatoeba.org/eng/terms_of_use",
        url=(
            "https://downloads.tatoeba.org/exports/per_language/eng/"
            "eng_sentences.tsv.bz2"
        ),
    ),
    "tatoeba_links": Source(
        key="tatoeba_links",
        license="CC-BY-2.0-FR",
        homepage="https://tatoeba.org/eng/terms_of_use",
        url="https://downloads.tatoeba.org/exports/links.tar.bz2",
    ),
    "tatoeba_audio": Source(
        key="tatoeba_audio",
        license="CC-BY-2.0-FR",
        homepage="https://tatoeba.org/eng/terms_of_use",
        url=(
            "https://downloads.tatoeba.org/exports/"
            "sentences_with_audio.tar.bz2"
        ),
        optional=True,
    ),
    "kanjialive": Source(
        key="kanjialive",
        license="CC-BY-4.0",
        homepage="https://kanjialive.com/",
        url="https://media.kanjialive.com/examples_audio/audio-mp3.zip",
        optional=True,
    ),
    "kanjialive_data": Source(
        key="kanjialive_data",
        license="CC-BY-4.0",
        homepage="https://kanjialive.com/",
        url=(
            "https://raw.githubusercontent.com/kanjialive/"
            "kanji-data-media/master/language-data/ka_data.csv"
        ),
        optional=True,
    ),
}
"""
A dictionary mapping upstream source's names to their
[`Source`][kotobase.db.builder.config.Source] definition

Includes all upstream sources used to build the `kotobase` database
"""

# --- Filesystem layout ---

ENV_CACHE_DIR = "KOTOBASE_CACHE_DIR"
"""
Defines the name of the environment variable that overrides the default cache
directory in which the databses are saved
"""

DB_FILENAME = "kotobase.db"
"""
Defines the file name of the core database within the cache directory
"""

AUDIO_DB_FILENAME = "kotobase-audio.db"
"""
Defines the File name of the optional audio database within the cache directory
"""

RELEASE_REPO = "svdC1/kotobase"
"""
Defines the GitHub repository which hosts the pre-built database assets
"""

DB_ASSET = "kotobase.db.zst"
"""
Defines the file name of of the `zstandard` compressed core database released
as an asset in `RELEASE_REPO`
"""

AUDIO_ASSET = "kotobase-audio.db.zst"
"""
Defines the file name of the `zstandard` compressed audio database released as
an asset in `RELEASE_REPO`
"""

HOST_STORAGE = PlatformDirs(
    appname="kotobase",
    appauthor=False,
    ensure_exists=False,
)
r"""
Filesystem locations used to store the kotobase databases

All user-writable paths derive from `platformdirs` and are keyed by the app's
name
"""

DEFAULT_CACHE_DIR = HOST_STORAGE.user_cache_path
"""
The default directory in which the databases are stored when ENV_CACHE_DIR is
not set
"""

USER_AGENT = "kotobase-build (+https://github.com/svdC1/kotobase)"
"""
The User-Agent used for all HTTP requests made by the kotobase package
"""


def cache_dir() -> Path:
    """
    Resolve the kotobase cache directory

    The directory is taken from the `KOTOBASE_CACHE_DIR` environment variable
    when set, otherwise it falls back to the per-user cache location reported
    by `platformdirs`

    Returns:
        The resolved cache directory, which may not exist yet
    """
    override = os.environ.get(ENV_CACHE_DIR)
    if override is not None:
        return Path(override).resolve()
    return DEFAULT_CACHE_DIR


def raw_dir() -> Path:
    """
    Resolve the directory that holds raw upstream source downloads

    Returns:
        The raw download directory inside the cache directory
    """
    return cache_dir() / "raw"


def db_path() -> Path:
    """
    Resolves the file path of the compiled core database

    Returns:
        The path of the core `SQLite` database inside the cache directory
    """
    return cache_dir() / DB_FILENAME


def audio_db_path() -> Path:
    """
    Resolve the path of the optional audio pack database

    Returns:
        The path of the audio `SQLite` database inside the cache directory
    """
    return cache_dir() / AUDIO_DB_FILENAME


def ensure_dirs() -> None:
    """
    Create the cache and raw download directories when they are missing
    """
    raw_dir().mkdir(parents=True, exist_ok=True)


# --- Shipped Package Data (Tanos JLPT) ---

JLPT_KINDS = ("vocab", "kanji", "grammar")
"""
The 3 processed `Tanos JLPT` list kinds in `JSON` format shipped with the
package
"""

JLPT_LEVELS = (1, 2, 3, 4, 5)
"""
The five JLPT levels, where 1 is hardest and 5 is easiest
"""


def _package_path(*parts: str) -> Path:
    """
    Resolves a path inside the installed `kotobase` package

    Uses `importlib.resources` to correctly look up the path regardless of how
    the package was installed

    Args:
        *parts (str): Path segments relative to the package root

    Returns:
        The concrete filesystem path to the resource
    """
    root = resources.files("kotobase")
    return Path(str(root.joinpath(*parts)))


def jlpt_file(kind: str, level: int) -> Path:
    """
    Resolves the path to a single processed `Tanos JLPT` list `JSON` file
    shipped in the package

    Args:
        kind (str): One of the values in
            [`JLPT_KINDS`][kotobase.db.builder.config.JLPT_KINDS]
        level (int): A JLPT level from 1 to 5

    Returns:
        The absolute path to the file within the installed package

    Raises:
        ValueError: If `kind` is not a known JLPT kind or `level` is out of
            range
    """
    if kind not in JLPT_KINDS:
        raise ValueError(f"Unknown JLPT Kind: {kind!r}")

    if level not in JLPT_LEVELS:
        raise ValueError(f"JLPT Level Out Of Range: {level!r}")

    return (_package_path("data", "jlpt") / f"{kind}_n{level}.json").resolve()
