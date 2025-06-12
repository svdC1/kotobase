from __future__ import annotations
from functools import lru_cache
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from kotobase.db.database import get_db
from kotobase.core import datatypes as dt
from kotobase.db import models as orm
__all__ = ["JMNeDictRepo"]


class JMNeDictRepo:
    """Name-dictionary look-ups (JMnedict)."""

    @staticmethod
    @lru_cache(maxsize=40_000)
    def by_id(entry_id: int) -> Optional[dt.JMNeDictEntryDTO]:
        with get_db() as s:
            row = s.get(
                orm.JMnedictEntry,
                entry_id,
                options=(
                    joinedload(orm.JMnedictEntry.kana),
                    joinedload(orm.JMnedictEntry.kanji),
                ),
            )
        return dt.map_jmnedict(row) if row else None

    # Simple LIKE search
    # (name dictionaries rarely need wildcards beyond head/tail)
    @staticmethod
    def search(form: str, limit: int | None = 50) -> List[dt.JMNeDictEntryDTO]:
        pattern = form.replace("*", "%")
        with get_db() as s:
            stmt = (
                select(orm.JMnedictEntry)
                .join(orm.JMnedictEntry.kana, isouter=True)
                .join(orm.JMnedictEntry.kanji, isouter=True)
                .where(
                    orm.JMnedictKana.text.like(pattern)
                    | orm.JMnedictKanji.text.like(pattern)
                )
                .options(
                    joinedload(orm.JMnedictEntry.kana),
                    joinedload(orm.JMnedictEntry.kanji),
                )
            )
            if limit:
                stmt = stmt.limit(limit)
            rows = s.scalars(stmt).unique().all()
        return dt.map_many(dt.map_jmnedict, rows)
