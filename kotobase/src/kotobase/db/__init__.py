"""
Kotobase's Database Layer

abstract: Contents
    - The [`SQAlchemy ORM Models`][kotobase.db.models] that define the
      database's schema

    - Cached, process-scope
      [`SQAlchemy Engine + Session Maker`][kotobase.db.connection] to connect
      with the database

    - The [`Unit Of Work`][kotobase.db.uow] and [`Repos`][kotobase.db.repos]
      that abstract raw database queries

    - The [`Data-Transfer-Object`][kotobase.db.dtos] dataclasses that
      aggregate the information stored in the database and isolate its internal
      structure from the [`Public API`][kotobase.api] and [`CLI`][kotobase.cli]

    - The [`Build Pipeline`][kotobase.db.builder] that compiles the database
      from upstream sources
"""

from . import builder, connection, dtos, models, repos, uow
from .connection import session_scope
from .models import Base
from .uow import UnitOfWork

__all__ = [
    "Base",
    "UnitOfWork",
    "builder",
    "connection",
    "dtos",
    "models",
    "repos",
    "session_scope",
    "uow",
]
