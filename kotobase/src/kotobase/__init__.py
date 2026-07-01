"""
Comprehensive Japanese Language Database

Kotobase aggregates several openly licensed Japanese language sources into one
`SQLite` database and exposes simple programmatic access to it

The database can be built locally or downloaded as a pre-built release, then
queried through [`Kotobase`][kotobase.api.Kotobase],
which returns plain data transfer objects

This module re-exports the public API. Everything listed in `__all__` is
covered by semantic versioning
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from .api import Kotobase
from .db.dtos import (
    AudioDTO,
    FuriganaDTO,
    GlossDTO,
    JLPTGrammarDTO,
    JLPTKanjiDTO,
    JLPTVocabDTO,
    JMDictEntryDTO,
    JMNeDictEntryDTO,
    KanaFormDTO,
    KanjiDTO,
    KanjiFormDTO,
    LookupResult,
    NameTranslationDTO,
    RadicalDTO,
    SenseDTO,
    SentenceDTO,
)
from .exceptions import (
    APIError,
    AudioDatabaseNotFoundError,
    DatabaseError,
    DatabaseExistsError,
    DatabaseNotFoundError,
    DownloadError,
    KotobaseError,
    MalformedSourceError,
    SourceExtractionError,
)

try:
    __version__ = version("kotobase")
except PackageNotFoundError:
    __version__ = "0.0.0"

__all__ = [
    "APIError",
    "AudioDTO",
    "AudioDatabaseNotFoundError",
    "DatabaseError",
    "DatabaseExistsError",
    "DatabaseNotFoundError",
    "DownloadError",
    "FuriganaDTO",
    "GlossDTO",
    "JLPTGrammarDTO",
    "JLPTKanjiDTO",
    "JLPTVocabDTO",
    "JMDictEntryDTO",
    "JMNeDictEntryDTO",
    "KanaFormDTO",
    "KanjiDTO",
    "KanjiFormDTO",
    "Kotobase",
    "KotobaseError",
    "LookupResult",
    "MalformedSourceError",
    "NameTranslationDTO",
    "RadicalDTO",
    "SenseDTO",
    "SentenceDTO",
    "SourceExtractionError",
    "__version__",
]
