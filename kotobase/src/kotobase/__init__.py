"""
Kotobase is a Japanese language Python package which provides simple
programmatic access to various data sources via a pre-built database
which is updated weekly.
"""

from .db.database import get_db
from .api import Kotobase
from .db import models
from . import (core,
               api,
               db,
               db_builder,
               repos,
               cli)


__all__ = ["Kotobase",
           "get_db",
           "models",
           "core",
           "api",
           "db",
           "db_builder",
           "repos",
           "cli"]
