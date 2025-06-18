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
        with get_db() as s:
            # JMnedictEntry has no relationships, so no need for joinedload
            row = s.get(orm.JMnedictEntry, entry_id)
        return dt.map_jmnedict(row) if row else None

    # Simple LIKE search
    # (name dictionaries rarely need wildcards beyond head/tail)
    @staticmethod
    def search(form: str, limit: int | None = 50) -> List[dt.JMNeDictEntryDTO]:
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
