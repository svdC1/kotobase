from __future__ import annotations

import concurrent.futures as _cf
from functools import lru_cache
from typing import (List,
                    Dict,
                    Optional)

from kotobase.core.datatypes import (
    LookupResult,
    KanjiDTO,
    JMDictEntryDTO,
    JMNeDictEntryDTO,
    )
from kotobase.repos.jmdict import JMDictRepo
from kotobase.repos.jmnedict import JMNeDictRepo
from kotobase.repos.kanji import KanjiRepo
from kotobase.repos.jlpt import JLPTRepo
from kotobase.repos.sentences import SentenceRepo


class Kotobase:
    """
    Stateless class that orchestrates the individual repositories and
    returns rich, serialisable objects.
    """
    # Core
    def lookup(
        self,
        word: str,
        *,
        wildcard: bool = False,
        include_names: bool = False,
        sentence_limit: int = 50,
    ) -> LookupResult:
        """
        Comprehensive word lookup.

        Parameters
        ----------
        word : str
            The query string (kana, kanji, or romaji transliteration).
            Supports SQL wildcards '*' or '%'.
        wildcard : bool, default False
            If True, passes wildcards through unchanged.  If False,
            the search is exact (JMdict) but Tatoeba uses `%word%`
            containment.
        include_names : bool, default False
            Also query JMnedict (proper names).  Can be slow on very
            broad wildcards.
        sentence_limit : int, default 50
            Maximum number of Tatoeba sentences to fetch.

        Returns
        -------
        LookupResult
        """
        # 1. Find dictionary entries (JMdict & optionally JMnedict)
        entries: List[JMDictEntryDTO | JMNeDictEntryDTO] = []
        entries.extend(
            JMDictRepo.search_form(word, limit=None if wildcard else 50))
        if include_names:
            entries.extend(JMNeDictRepo.search(word, limit=50))

        # 2. Extract unique kanji found in the *query* itself
        kanji_chars = [c for c in word if "\u4e00" <= c <= "\u9fff"]
        kanji_info: List[KanjiDTO] = KanjiRepo.bulk_fetch(kanji_chars)

        # 3. Parallel extra look-ups (JLPT + sentences) -----------------
        with _cf.ThreadPoolExecutor(max_workers=3) as pool:
            f_vocab = pool.submit(JLPTRepo.vocab_by_word, word)
            f_levels = pool.submit(JLPTRepo.kanji_levels, kanji_chars)
            f_grammar = pool.submit(JLPTRepo.grammar_entries_like, word)
            f_sent = pool.submit(
                SentenceRepo.search_containing,
                word,
                limit=sentence_limit,
                wildcard=wildcard,
            )

            jlpt_vocab = f_vocab.result()
            jlpt_kanji_levels: Dict[str, int] = f_levels.result()
            jlpt_grammar = f_grammar.result()
            sentences = f_sent.result()

        # 4. Aggregate
        return LookupResult(
            word=word,
            entries=entries,
            kanji=kanji_info,
            jlpt_vocab=jlpt_vocab,
            jlpt_kanji_levels=jlpt_kanji_levels,
            jlpt_grammar=jlpt_grammar,
            examples=sentences,
        )

    # Convenience Wrappers

    @staticmethod
    @lru_cache(maxsize=10_000)
    def kanji(literal: str):
        """Return a single KanjiDTO (or None)."""
        return KanjiRepo.by_literal(literal)

    @staticmethod
    @lru_cache(maxsize=20_000)
    def jlpt_level(word: str) -> Optional[int]:
        """Shortcut – just return JLPT vocab level for a word."""
        dto = JLPTRepo.vocab_by_word(word)
        return dto.level if dto else None

    @staticmethod
    def sentences(text: str, *, limit: int = 20):
        """Fetch Japanese Tatoeba sentences containing *text*."""
        return SentenceRepo.search_containing(text, limit=limit)

    def __call__(self, word: str, **kwargs):
        """Alias for `lookup` so you can `Kotobase()(word)`."""
        return self.lookup(word, **kwargs)

    # Context Manager
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        # Propagate Exceptions
        return False


__all__ = ["Kotobase"]
