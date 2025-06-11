from kotobase.db.database import get_db
from kotobase.db.models import (JMDictEntry,
                                JMDictKanji,
                                JMDictKana,
                                JMnedictEntry,
                                Kanjidic,
                                TatoebaSentence,
                                JlptVocab,
                                JlptKanji,
                                JlptGrammar
                                )
from sqlalchemy.orm import joinedload
from sqlalchemy import or_


class Kotobase:
    """
    An API for querying the Kotobase database.
    This class can be used as a context manager.
    """
    def __init__(self):
        self._db_context = get_db()
        self.db = self._db_context.__enter__()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._db_context.__exit__(exc_type, exc_val, exc_tb)

    def find_word(self, query: str):
        """
        Finds a word in JMDict by either its kanji or kana representation.
        """
        query_obj = self.db.query(JMDictEntry).options(
            joinedload(JMDictEntry.kanji),
            joinedload(JMDictEntry.kana),
            joinedload(JMDictEntry.senses)
        )

        results = query_obj.join(
            JMDictEntry.kanji,
            isouter=True).join(JMDictEntry.kana,
                               isouter=True).filter(
            or_(
                JMDictKanji.text == query,
                JMDictKana.text == query
            )
        ).all()

        return results

    def find_kanji(self, literal: str):
        """
        Finds a kanji in Kanjidic by its literal character.
        """
        return self.db.query(Kanjidic).filter(
            Kanjidic.literal == literal).first()

    def get_jmdict_entries(self):
        """Returns all entries from JMDict."""
        return self.db.query(JMDictEntry).all()

    def get_jmnedict_entries(self):
        """Returns all entries from JMnedict."""
        return self.db.query(JMnedictEntry).all()

    def get_kanjidic_entries(self):
        """Returns all entries from Kanjidic."""
        return self.db.query(Kanjidic).all()

    def get_tatoeba_sentences(self):
        """Returns all sentences from Tatoeba."""
        return self.db.query(TatoebaSentence).all()

    def get_jlpt_vocab(self, level: int):
        """
        Gets the JLPT vocabulary list for a given level.
        """
        if not 1 <= level <= 5:
            raise ValueError("JLPT level must be between 1 and 5.")
        return self.db.query(JlptVocab).filter(JlptVocab.level == level).all()

    def get_jlpt_kanji(self, level: int):
        """
        Gets the JLPT kanji list for a given level.
        """
        if not 1 <= level <= 5:
            raise ValueError("JLPT level must be between 1 and 5.")
        return self.db.query(JlptKanji).filter(JlptKanji.level == level).all()

    def get_jlpt_grammar(self, level: int):
        """
        Gets the JLPT grammar list for a given level.
        """
        if not 1 <= level <= 5:
            raise ValueError("JLPT level must be between 1 and 5.")
        return self.db.query(JlptGrammar).filter(
            JlptGrammar.level == level).all()

    def lookup_word(self, word: str):
        """
        Performs a comprehensive lookup of a word, gathering information
        from all connected data sources.
        """
        # 1. Fetch JMDict entries
        jmdict_entries = self.find_word(word)

        # 2. Get all unique kanji in the word
        kanji_in_word = list(
            set([char for char in word if '\u4e00' <= char <= '\u9faf']))

        # 3. Fetch Kanjidic entries for each kanji
        kanjidic_entries = [self.find_kanji(k) for k in kanji_in_word]

        # 4. Find Tatoeba sentences
        tatoeba_sentences = self.db.query(TatoebaSentence).filter(
            TatoebaSentence.text.like(f"%{word}%")).all()

        # 5. Determine JLPT vocabulary level
        jlpt_vocab_entry = self.db.query(JlptVocab).filter(or_(
            JlptVocab.kanji == word, JlptVocab.hiragana == word)).first()
        jlpt_vocab_level = jlpt_vocab_entry.level if jlpt_vocab_entry else None

        # 6. Find JLPT kanji levels
        jlpt_kanji_levels = {k.kanji: k.level for k in self.db.query(
            JlptKanji).filter(JlptKanji.kanji.in_(kanji_in_word)).all()}

        # 7. Find JLPT grammar entries
        grammar_query = word.replace('～', '%')
        jlpt_grammar_entries = self.db.query(JlptGrammar).filter(
            JlptGrammar.grammar.like(f"{grammar_query}%")).all()

        return {
            "jmdict_entries": jmdict_entries,
            "kanjidic_entries": kanjidic_entries,
            "tatoeba_sentences": tatoeba_sentences,
            "jlpt_vocab_level": jlpt_vocab_level,
            "jlpt_kanji_levels": jlpt_kanji_levels,
            "jlpt_grammar_entries": jlpt_grammar_entries,
        }
