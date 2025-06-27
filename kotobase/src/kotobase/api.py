"""
This module defines the main kotobase API through the `Kotobase` class
to make queries to the database and return data objects.
"""

from __future__ import annotations

import concurrent.futures as _cf
from typing import (List,
                    Dict,
                    Optional)

from kotobase.core.datatypes import (
    LookupResult,
    KanjiDTO,
    JMDictEntryDTO,
    JMNeDictEntryDTO,
    SentenceDTO
    )
import re
from kotobase.db_builder.config import DB_BUILD_LOG_PATH
from kotobase.repos.jmdict import JMDictRepo
from kotobase.repos.jmnedict import JMNeDictRepo
from kotobase.repos.kanji import KanjiRepo
from kotobase.repos.jlpt import JLPTRepo
from kotobase.repos.sentences import SentenceRepo


class Kotobase:
    """
    Stateless class that orchestrates the individual repositories and
    returns serialisable objects.
    """
    def lookup(
        self,
        word: str,
        *,
        wildcard: bool = False,
        include_names: bool = False,
        sentence_limit: int = 50,
        entry_limit: Optional[int] = None
    ) -> LookupResult:
        """
        Comprehensive word lookup.

        Args:
          word (str): The query string (kana, kanji)
                      Supports SQL wildcards '*' or '%'.
          wildcard (bool): If True, passes wildcards through unchanged.
                           If False, the search is exact (JMdict) but
                           Tatoeba uses `%word%` containment.
          include_names (bool): Also query JMnedict (proper names).
                                Can be slow on very broad wildcards.
          sentence_limit (int): Maximum number of Tatoeba sentences to fetch.

          entry_limit (int, optional): Maximum number of entries to fetch.

        Returns:
            LookupResult: LookupResult Object.
        """

        # Extract unique kanji found in the query
        kanji_chars = [c for c in word if "\u4e00" <= c <= "\u9fff"]
        # Strip whitespace
        word = word.strip()
        entries: List[JMDictEntryDTO | JMNeDictEntryDTO] = []
        # Parallel  Lookups
        with _cf.ThreadPoolExecutor(max_workers=7) as pool:
            f_jmdict = pool.submit(JMDictRepo.search_form,
                                   word,
                                   wildcard=wildcard,
                                   limit=entry_limit
                                   )
            f_jmnedict = pool.submit(JMNeDictRepo.search,
                                     word,
                                     limit=entry_limit
                                     ) if include_names else None
            f_kanji = pool.submit(KanjiRepo.bulk_fetch, kanji_chars)
            f_vocab = pool.submit(JLPTRepo.vocab_by_word, word)
            f_levels = pool.submit(JLPTRepo.kanji_levels, kanji_chars)
            f_grammar = pool.submit(JLPTRepo.grammar_entries_like, word)
            f_sent = pool.submit(
                SentenceRepo.search_containing,
                word,
                limit=sentence_limit,
                wildcard=wildcard,
            )
            # Retrieve results
            entries.extend(f_jmdict.result())
            if f_jmnedict:
                entries.extend(f_jmnedict.result())

            kanji_info: List[KanjiDTO] = f_kanji.result()
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

    # Get Database Info From Build Log
    @staticmethod
    def db_info() -> Dict[str, str]:
        """
        Return a dictionary containing variables from
        Database build log file, if it exists.

        Raises:
          EnvironmentError: If file doeesn't exist.
        """
        if not DB_BUILD_LOG_PATH.exists():
            raise EnvironmentError("Database Build Log File Not Found")
        raw_log = DB_BUILD_LOG_PATH.read_text()
        info = {}
        matches = {
            "build_date": re.search(r'^BUILD_DATE=(.+)$',
                                    raw_log,
                                    re.MULTILINE),
            "build_time": re.search(r'^BUILD_TIME=(.+)$',
                                    raw_log,
                                    re.MULTILINE),
            "size_mb": re.search(r'^SIZE_MB=(.+)$',
                                 raw_log,
                                 re.MULTILINE)
            }
        for k, v in matches.items():
            if v:
                info[k] = v.group(1)
            else:
                info[k] = "N/A"
        return info

    # Convenience Wrappers

    @staticmethod
    def kanji(literal: str) -> Optional[KanjiDTO]:
        """
        Return a single KanjiDTO (or None).

        Args:
          literal (str): Kanji Literal String.

        Returns:
          KanjiDTO: Kanji data object
        """
        return KanjiRepo.by_literal(literal)

    @staticmethod
    def jlpt_level(word: str) -> Optional[int]:
        """
        Shortcut – just return JLPT vocab level for a word.

        Args:
          word (str): Word to search for.

        Returns:
          int: The JLPT Level
        """
        dto = JLPTRepo.vocab_by_word(word)
        return dto.level if dto else None

    @staticmethod
    def sentences(text: str,
                  *,
                  limit: int = 20
                  ) -> List[SentenceDTO]:
        """
        Fetch Japanese Tatoeba sentences containing *text*.

        Args:
          text (str): String text to search for
          limit (int): How many sentences to return.
        """
        return SentenceRepo.search_containing(text, limit=limit)

    def __call__(self,
                 word: str,
                 *,
                 wildcard: bool = False,
                 include_names: bool = False,
                 sentence_limit: int = 50,
                 entry_limit: Optional[int] = None
                 ) -> LookupResult:
        """
        Comprehensive word lookup.

        Args:
          word (str): The query string (kana, kanji)
                      Supports SQL wildcards '*' or '%'.
          wildcard (bool): If True, passes wildcards through unchanged.
                           If False, the search is exact (JMdict) but
                           Tatoeba uses `%word%` containment.
          include_names (bool): Also query JMnedict (proper names).
                                Can be slow on very broad wildcards.
          sentence_limit (int): Maximum number of Tatoeba sentences to fetch.

          entry_limit (int, optional): Maximum number of entries to fetch.

        Returns:
            LookupResult: LookupResult Object.
        """

        return self.lookup(word=word,
                           wildcard=wildcard,
                           include_names=include_names,
                           sentence_limit=sentence_limit,
                           entry_limit=entry_limit
                           )


__all__ = ["Kotobase"]
