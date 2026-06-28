"""
Defines the `Build Pipeline` which constructs kotobase's database from
upstream sources

abstract: Contains
    - Utilities to [`Download`][kotobase.db.builder.download] the upstream
      sources and pull the pre-built versions of the database from the
      [`kotobase GitHub Repository`](https://github.com/svdC1/kotobase)
      releases

    - The [`extractors`][kotobase.db.builder.extractors] module, which turns
      each upstream source into database rows. It holds the shared parsing
      helpers, one `extract_{source}` function per source and the registry the
      builder runs

    - The functions that [`builds`][kotobase.db.builder.build] the core
      database and the additional `audio-package` database (appended to the
      core database when present by the
      [`Engine Builder`][kotobase.db.connection.get_engine]) by running the
      [`extractors`][kotobase.db.builder.extractors] registry and writing the
      rows into the tables

    - [`Configuration`][kotobase.db.builder.config] module defining where the
      database will be stored in the host (uses `platformdirs`) along with
      all upstream source metadata
"""

from . import config
from .build import build_audio, build_core, compress
from .download import pull_audio, pull_db

__all__ = [
    "build_audio",
    "build_core",
    "compress",
    "config",
    "pull_audio",
    "pull_db",
]
