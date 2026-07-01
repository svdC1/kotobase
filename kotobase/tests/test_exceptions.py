"""
Tests for the exception hierarchy, its top-level re-exports, and the
repository-level wrapping of unexpected database failures
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import kotobase
from kotobase.db.repos import JMDictRepo
from kotobase.exceptions import (
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


def test_domain_bases_descend_from_root() -> None:
    """
    The four domain bases can all be caught as KotobaseError
    """
    for exc in (DatabaseError, SourceExtractionError, DownloadError, APIError):
        assert issubclass(exc, KotobaseError)


def test_database_leaves_descend_from_database_error() -> None:
    """
    Every database leaf can be caught as a DatabaseError
    """
    for exc in (
        DatabaseNotFoundError,
        AudioDatabaseNotFoundError,
        DatabaseExistsError,
    ):
        assert issubclass(exc, DatabaseError)


def test_extraction_leaf_descends_from_extraction_error() -> None:
    """
    MalformedSourceError can be caught as a SourceExtractionError
    """
    assert issubclass(MalformedSourceError, SourceExtractionError)


def test_exceptions_are_reexported_at_top_level() -> None:
    """
    The hierarchy is importable straight from the top-level package
    """
    assert kotobase.KotobaseError is KotobaseError
    assert kotobase.APIError is APIError
    assert kotobase.AudioDatabaseNotFoundError is AudioDatabaseNotFoundError


def test_repo_wraps_unexpected_database_error() -> None:
    """
    A query against a schema-less database surfaces as a DatabaseError
    """
    engine = create_engine("sqlite:///:memory:")
    with Session(engine) as session:
        repo = JMDictRepo(session)
        with pytest.raises(DatabaseError):
            repo.search_form("語")
