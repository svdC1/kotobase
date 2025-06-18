from __future__ import annotations
from typing import List, Optional, Dict, Iterable
from kotobase.db.database import get_db
from kotobase.core import datatypes as dt
from kotobase.db import models as orm

__all__ = ["KanjiRepo"]


class KanjiRepo:
    """
    Queries Kanji related Tables of the database
    """

    # ── caches: literal → DTO ──────────────────────────────────────────
    _cache: Dict[str, dt.KanjiDTO] = {}

    @staticmethod
    def by_literal(lit: str) -> Optional[dt.KanjiDTO]:
        """
        Retrieve Kanji by literal
        """
        if lit in KanjiRepo._cache:
            return KanjiRepo._cache[lit]

        with get_db() as s:
            row = (
                s.query(orm.Kanjidic)
                .filter(orm.Kanjidic.literal == lit)
                .first()
            )
            if not row:
                return None

            jlpt_row = (
                s.query(orm.JlptKanji)
                .filter(orm.JlptKanji.kanji == lit)
                .first()
            )
            dto = dt.map_kanjidic(
                row, jlpt_tanos_level=jlpt_row.level if jlpt_row else None
            )
            KanjiRepo._cache[lit] = dto
            return dto

    # bulk helper – keeps order of incoming sequence  --------------------
    @staticmethod
    def bulk_fetch(chars: Iterable[str]) -> List[dt.KanjiDTO]:
        """
        Bulk-Fetch Kanji for performance.
        """
        out: List[dt.KanjiDTO] = []
        missing: List[str] = []
        for c in chars:
            cached = KanjiRepo._cache.get(c)
            if cached:
                out.append(cached)
            else:
                missing.append(c)

        if missing:
            with get_db() as s:
                rows = (
                    s.query(orm.Kanjidic)
                    .filter(orm.Kanjidic.literal.in_(missing))
                    .all()
                )
                jlpt_map = {
                    r.kanji: r.level
                    for r in s.query(orm.JlptKanji)
                    .filter(orm.JlptKanji.kanji.in_(missing))
                    .all()
                }
            for r in rows:
                dto = dt.map_kanjidic(
                    r, jlpt_tanos_level=jlpt_map.get(r.literal)
                )
                KanjiRepo._cache[r.literal] = dto
                out.append(dto)

        # preserve original order
        ordering = {c: i for i, c in enumerate(chars)}
        out.sort(key=lambda k: ordering[k.literal])
        return out
