from __future__ import annotations
from functools import lru_cache
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from kotobase.db.database import get_db
from kotobase.core import datatypes as dt
from kotobase.db import models as orm

__all__ = ["JMDictRepo"]


class JMDictRepo:
    """Query JMDict Related Tables of Database"""

    # ── single-row lookups ──────────────────────────────────────────────

    @staticmethod
    @lru_cache(maxsize=100_000)
    def by_id(entry_id: int) -> Optional[dt.JMDictEntryDTO]:
        """
        Retrieve Entry by id.
        """
        with get_db() as s:
            row = s.get(
                orm.JMDictEntry,
                entry_id,
                options=(
                    joinedload(orm.JMDictEntry.kana),
                    joinedload(orm.JMDictEntry.kanji),
                    joinedload(orm.JMDictEntry.senses),
                ),
            )
        return dt.map_jmdict(row) if row else None

    # ── search helpers ──────────────────────────────────────────────────

    @staticmethod
    def search_form(form: str,
                    /,
                    limit: int | None = 50
                    ) -> List[dt.JMDictEntryDTO]:
        """
        Exact or wildcard search across *kana* **and** *kanji*.
        - '*' or '%' acts as SQL wildcard
        - Case-sensitive on purpose (JMdict is already normalised hiragana/
          katakana vs. kanji)
        """
        pattern = form.replace("*", "%")

        with get_db() as s:
            # 1 - IDs Only
            id_stmt = (
                select(orm.JMDictEntry.id)
                .join(orm.JMDictEntry.kana, isouter=True)
                .join(orm.JMDictEntry.kanji, isouter=True)
                .where(
                    orm.JMDictKana.text.like(pattern)
                    | orm.JMDictKanji.text.like(pattern)
                )
                .distinct()
                .limit(limit)
            )
            ids = [row[0] for row in s.execute(id_stmt)]
            if not ids:
                return []
            # 2- bulk-fetch full objects
            rows = (
                s.query(orm.JMDictEntry)
                .filter(orm.JMDictEntry.id.in_(ids))
                .options(
                    joinedload(orm.JMDictEntry.kana),
                    joinedload(orm.JMDictEntry.kanji),
                    joinedload(orm.JMDictEntry.senses),
                )
                .all()
            )

        return dt.map_many(dt.map_jmdict, rows)
