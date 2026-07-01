"""
Defines kotobase's exception hierarchy
"""

# --- Package-Wide Base ---


class KotobaseError(Exception):
    """
    Common base class for all exceptions raised by kotobase
    """


# --- Domain Bases ---


class DatabaseError(KotobaseError):
    """
    Common base class for all exceptions resulting from database management
    operations

    These errors indicate that there has been a problem querying or building
    the `SQLite` databases that kotobase relies on
    """


class SourceExtractionError(KotobaseError):
    """
    Common base class for all exceptions resulting from upstream source data
    parsing

    These errors indicate that an extractor couldn't produce valid database
    rows from an upstream data source
    """


class DownloadError(KotobaseError):
    """
    Common base class for all exceptions resulting from network downloads

    These errors indicate that the upstream data source files, or the pre-built
    databases couldn't be fetched
    """


class APIError(KotobaseError):
    """
    Common base class for all exceptions coming directly from kotobase's
    top-level [`API`][kotobase.api]

    These errors indicate that the top-level
    [`Kotobase`][kotobase.api.Kotobase] received invalid arguments or had
    problems using the [`DTOs`][kotobase.db.dtos] produced by the
    [`repos`][kotobase.db.repos]
    """


# --- Database Errors ---


class DatabaseNotFoundError(DatabaseError):
    """
    Raised when a query to the core database is attempted before the database
    exists
    """


class AudioDatabaseNotFoundError(DatabaseError):
    """
    Raised when audio bytes are requested, but the optional audio database pack
    is not installed
    """


class DatabaseExistsError(DatabaseError):
    """
    Raised when a build or pull would overwrite a database that already exists
    and the caller did not request a forced rebuild
    """


# --- Extraction Errors ---


class MalformedSourceError(SourceExtractionError):
    """
    Raised when an upstream source does not follow the format expected by its
    extractor, indicating that it might be malformed
    """
