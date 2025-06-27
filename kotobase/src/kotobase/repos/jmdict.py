"""
This module defines the `JMDictRepo` class used for querying
data extracted from the JMDict XML file in the database.
"""


from __future__ import annotations
from functools import lru_cache
from typing import List, Optional

from sqlalchemy.orm import joinedload, selectinload

from kotobase.db.database import get_db
from kotobase.core import datatypes as dt
from kotobase.db import models as orm

__all__ = ["JMDictRepo"]


class JMDictRepo:
    """
    Queries JMDict Related Tables of Database
    """

    # ── single-row lookups ──────────────────────────────────────────────

    @staticmethod
    @lru_cache(maxsize=100_000)
    def by_id(entry_id: int) -> Optional[dt.JMDictEntryDTO]:
        """
        Retrieve Entry by id.

        Args:
          entry_id (int): Entry ID in database.

        Returns:
          JMDictEntryDTO: JMDict Entry Data Object.
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
    @lru_cache(maxsize=100_000)
    def search_form(form: str,
                    /,
                    *,
                    wildcard: bool = False,
                    limit: Optional[int] = 50
                    ) -> List[dt.JMDictEntryDTO]:
        """
        Exact or wildcard search across `kana` and `kanji`.

        Args:
          form (str): Query string.

          wildcard (bool): If true, treat `*` and `%` and wildcards and perform
                           a LIKE search. If false, pass wildcards unchanged
                           and perform a simple comparison search.

          limit (int, optional): Limit of entries to return, can be set to
                                 `None` for no limit.
        Returns:
          List[JMDictEntryDTO]: List of JMDictEntry data objects.
        """
        if wildcard:
            pattern = form.replace("*", "%")
            comparator_kana = orm.JMDictKana.text.like(pattern)
            comparator_kanji = orm.JMDictKanji.text.like(pattern)
        else:
            pattern = form
            comparator_kana = orm.JMDictKana.text == form
            comparator_kanji = orm.JMDictKanji.text == form

        with get_db() as s:
            rows = (
                s.query(orm.JMDictEntry)
                .filter(
                    orm.JMDictEntry.kana.any(comparator_kana) |
                    orm.JMDictEntry.kanji.any(comparator_kanji)
                )
                .options(
                    selectinload(orm.JMDictEntry.kana),
                    selectinload(orm.JMDictEntry.kanji),
                    selectinload(orm.JMDictEntry.senses),
                )
                .order_by(orm.JMDictEntry.rank,
                          orm.JMDictEntry.id
                          )
                .limit(limit)
                .all()
            )
            return dt.map_many(dt.map_jmdict, rows)
