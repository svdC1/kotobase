from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from contextlib import contextmanager
from functools import lru_cache
import threading


# Get the directory of the current file
file_dir = Path(__file__).resolve().parent

# Construct the path to the database file
DATABASE_URL = f"sqlite:///{file_dir / 'kotobase.db'}"


@lru_cache
def _engine():
    """Singleton SQLAlchemy engine (pooled)."""
    return create_engine(
        DATABASE_URL,
        future=True,
        connect_args={"check_same_thread": False},
        pool_size=8,
        max_overflow=16,
    )


_local = threading.local()


@contextmanager
def get_db():
    """
    Context-managed session that is *implicitly reused* if we’re already
    inside a DB context on the same thread.
    """
    new = not hasattr(_local, "db")
    if new:
        _local.db = Session(_engine(),
                            expire_on_commit=False,
                            autoflush=False)

    try:
        yield _local.db
    finally:
        if new:
            _local.db.close()
            del _local.db


__all__ = ["_engine", "file_dir", "DATABASE_URL", "get_db"]
