"""
This module defines the `JLPTRepo` class used for querying
data extracted from Jonathan Weller's website in the database.
"""

from __future__ import annotations
from typing import List, Optional, Dict, Iterable
from functools import lru_cache
from kotobase.db.database import get_db
from kotobase.core import datatypes as dt
from kotobase.db import models as orm
__all__ = ["JLPTRepo"]


class JLPTRepo:
    """
    Query JLPT Related Tables of Database
    """

    # ── vocab ───────────────────────────────────────────────────────────

    @staticmethod
    @lru_cache(maxsize=30_000)
    def vocab_by_word(word: str) -> Optional[dt.JLPTVocabDTO]:
        """
        Get vocabulary by word

        Args:
          word (str): Word to query

        Returns:
          JLPTVocabDTO: JLPT Vocab data object.
        """
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
        """
        Get Vocab JLPT levels

        Args:
          word (str): Word to query.

        Returns:
          int: JLPT level if existent.
        """
        dto = JLPTRepo.vocab_by_word(word)
        return dto.level if dto else None

    # Kanji Levels

    @staticmethod
    def kanji_levels(chars: Iterable[str]) -> Dict[str, int]:
        """
        Get Kanji levels with bulk search

        Args:
          chars (Iterable[str]): Iterable of character to query.

        Returns:
          Dict[str, int]: Dictionary with character keys and level values.
        """
        with get_db() as s:
            rows = (
                s.query(orm.JlptKanji)
                .filter(orm.JlptKanji.kanji.in_(chars))
                .all()
            )
        return {r.kanji: r.level for r in rows}

    # Grammar Lookup

    @staticmethod
    def grammar_entries_like(pattern: str) -> List[dt.JLPTGrammarDTO]:
        """
        Wildcard search for grammar patterns

        Args:
          pattern (str): Wildcard Pattern

        Returns:
          List[JLPTGrammarDTO]: List of JLPT Grammar data objects.
        """
        pattern = pattern.replace("～", "%").replace("*", "%")
        with get_db() as s:
            rows = (
                s.query(orm.JlptGrammar)
                .filter(
                    orm.JlptGrammar.grammar.like(f"{pattern}%", escape="\\"))
                .all()
            )
        return dt.map_many(dt.map_jlpt_grammar, rows)
