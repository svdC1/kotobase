"""
This module defines the `JMneDictRepo` class used for querying
data extracted from the JMneDict XML file in the database.
"""

from __future__ import annotations
from functools import lru_cache
from typing import List, Optional

from sqlalchemy import select, or_

from kotobase.db.database import get_db
from kotobase.core import datatypes as dt
from kotobase.db import models as orm
__all__ = ["JMNeDictRepo"]


class JMNeDictRepo:
    """
    Queries related to JMNeDict Tables of the database.
    """

    @staticmethod
    @lru_cache(maxsize=40_000)
    def by_id(entry_id: int) -> Optional[dt.JMNeDictEntryDTO]:
        """
        Retrieve Entry by id.

        Args:
          entry_id (int): Entry ID in database.

        Returns:
          JMNeDictEntryDTO: JMNeDict Entry Data Object.
        """
        with get_db() as s:
            row = s.get(orm.JMnedictEntry, entry_id)
        return dt.map_jmnedict(row) if row else None

    @staticmethod
    @lru_cache(maxsize=40_000)
    def search(form: str,
               limit: Optional[int] = 50
               ) -> List[dt.JMNeDictEntryDTO]:
        """
        LIKE search on JMNeDict table.

        Args:
          form (str): Query string.

          limit (int, optional): Limit of entries to return, can be set to
                                 `None` for no limit.
        Returns:
          List[JMNeDictEntryDTO]: List of JMNeDictEntry data objects.
        """
        pattern = form.replace("*", "%")
        with get_db() as s:
            stmt = (
                select(orm.JMnedictEntry)
                .where(
                    or_(
                        orm.JMnedictEntry.kana.like(pattern),
                        orm.JMnedictEntry.kanji.like(pattern)
                    )
                )
            )
            if limit:
                stmt = stmt.limit(limit)
            rows = s.scalars(stmt).all()
        return dt.map_many(dt.map_jmnedict, rows)
