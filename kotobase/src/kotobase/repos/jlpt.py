from __future__ import annotations
from typing import List, Optional, Dict, Iterable
from functools import lru_cache
from kotobase.db.database import get_db
from kotobase.core import datatypes as dt
from kotobase.db import models as orm
__all__ = ["JLPTRepo"]


class JLPTRepo:

    # ── vocab ───────────────────────────────────────────────────────────

    @staticmethod
    @lru_cache(maxsize=30_000)
    def vocab_by_word(word: str) -> Optional[dt.JLPTVocabDTO]:
        with get_db() as s:
            row = (
                s.query(orm.JlptVocab)
                .filter(
                    (orm.JlptVocab.kanji == word
                     ) | (orm.JlptVocab.hiragana == word))
                .first()
            )
        return dt.map_jlpt_vocab(row) if row else None

    @staticmethod
    def vocab_level(word: str) -> Optional[int]:
        dto = JLPTRepo.vocab_by_word(word)
        return dto.level if dto else None

    # ── kanji levels (bulk) ─────────────────────────────────────────────

    @staticmethod
    def kanji_levels(chars: Iterable[str]) -> Dict[str, int]:
        with get_db() as s:
            rows = (
                s.query(orm.JlptKanji)
                .filter(orm.JlptKanji.kanji.in_(chars))
                .all()
            )
        return {r.kanji: r.level for r in rows}

    # ── grammar lookup ─────────────────────────────────────────────────

    @staticmethod
    def grammar_entries_like(pattern: str) -> List[dt.JLPTGrammarDTO]:
        pattern = pattern.replace("～", "%").replace("*", "%")
        with get_db() as s:
            rows = (
                s.query(orm.JlptGrammar)
                .filter(
                    orm.JlptGrammar.grammar.like(f"{pattern}%", escape="\\"))
                .all()
            )
        return dt.map_many(dt.map_jlpt_grammar, rows)
