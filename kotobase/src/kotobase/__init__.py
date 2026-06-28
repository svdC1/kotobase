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
from .db.connection import AudioDatabaseNotFoundError, DatabaseNotFoundError
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
    Serializable,
)

try:
    __version__ = version("kotobase")
except PackageNotFoundError:
    __version__ = "0.0.0"

__all__ = [
    "AudioDTO",
    "AudioDatabaseNotFoundError",
    "DatabaseNotFoundError",
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
    "LookupResult",
    "NameTranslationDTO",
    "RadicalDTO",
    "SenseDTO",
    "SentenceDTO",
    "Serializable",
    "__version__",
]
