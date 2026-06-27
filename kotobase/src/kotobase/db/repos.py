"""
Read-access repositories for the kotobase database

Each repository wraps a single session and turns queries into data transfer
objects. Headword lookups use the normalized form tables, meaning searches use
the `gloss_fts` full text index, and Japanese substring searches over sentences
use `LIKE` containment, which is reliable for kanji and kana text

info: Session Management
    - Repositories never open their own session
    - The [`Unit Of Work`][kotobase.db.uow] owns one session and hands the
      same one to every repository it exposes
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import ColumnElement, func, select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, selectinload

from . import dtos
from .connection import AudioDatabaseNotFoundError
from .models import (
    Audio,
    Furigana,
    JlptGrammar,
    JlptKanji,
    JlptVocab,
    JMDictEntry,
    JMDictKana,
    JMDictKanji,
    JMDictSense,
    JMnedictEntry,
    JMnedictKana,
    JMnedictKanji,
    JMnedictTranslation,
    Kanji,
    KanjiQueryCode,
    KanjiRadical,
    KanjiStrokes,
    Radical,
    Sentence,
    SentenceLink,
    Tag,
)


class Repository:
    """
    Base class for a repository bound to a database session

    Attributes:
        session (Session): The session used for every query
    """

    def __init__(self, session: Session) -> None:
        """
        Binds the repository to a session

        Args:
            session (Session): The active session to query through
        """
        self.session = session


_JMDICT_LOAD = (
    selectinload(JMDictEntry.kanji),
    selectinload(JMDictEntry.kana),
    selectinload(JMDictEntry.senses).selectinload(JMDictSense.glosses),
)
"""
Eager-loading configuration for `JMdict` entries
"""


_JMDICT_ORDER = (
    JMDictEntry.is_common.desc(),
    JMDictEntry.freq_rank.is_(None),
    JMDictEntry.freq_rank,
    JMDictEntry.id,
)
"""
How `JMDict` entries should be ordered
"""


class JMDictRepo(Repository):
    """
    Repository that abstract queries for the JMdict tables
    """

    def by_id(self, entry_id: int) -> dtos.JMDictEntryDTO | None:
        """
        Fetches a single entry by its sequence number

        Args:
            entry_id (int): The JMdict sequence number

        Returns:
            The entry, or None when no entry has that id
        """
        entry = self.session.get(JMDictEntry, entry_id, options=_JMDICT_LOAD)
        return dtos.JMDictEntryDTO.from_orm(entry) if entry else None

    def _by_ids(self, ids: list[int]) -> list[dtos.JMDictEntryDTO]:
        """
        Fetches several entries by id, ordered by commonness, then frequency

        Args:
            ids (list[int]): The entry ids to fetch

        Returns:
            The matching entries as data transfer objects
        """
        if not ids:
            return []
        statement = (
            select(JMDictEntry)
            .where(JMDictEntry.id.in_(ids))
            .options(*_JMDICT_LOAD)
            .order_by(*_JMDICT_ORDER)
        )
        entries = self.session.scalars(statement).all()
        return [dtos.JMDictEntryDTO.from_orm(entry) for entry in entries]

    def search_form(
        self,
        form: str,
        *,
        wildcard: bool = False,
        limit: int | None = 50,
    ) -> list[dtos.JMDictEntryDTO]:
        """
        Searches entries by a written or reading form

        Args:
            form (str): The query form, where `*` and `%` act as wildcards when
                `wildcard` is True
            wildcard (bool): When True, treat the query as a `LIKE` pattern,
                otherwise match it exactly
            limit (int | None): Maximum entries to return, or None for no limit

        Returns:
            The matching entries as data transfer objects
        """
        kanji_match: ColumnElement[bool]
        kana_match: ColumnElement[bool]
        if wildcard:
            pattern = form.replace("*", "%")
            kanji_match = JMDictKanji.text.like(pattern)
            kana_match = JMDictKana.text.like(pattern)
        else:
            kanji_match = JMDictKanji.text == form
            kana_match = JMDictKana.text == form
        statement = (
            select(JMDictEntry)
            .where(
                JMDictEntry.kanji.any(kanji_match)
                | JMDictEntry.kana.any(kana_match)
            )
            .options(*_JMDICT_LOAD)
            .order_by(*_JMDICT_ORDER)
            .limit(limit)
        )
        entries = self.session.scalars(statement).all()
        return [dtos.JMDictEntryDTO.from_orm(entry) for entry in entries]

    def search_gloss(
        self,
        query: str,
        *,
        limit: int = 50,
    ) -> list[dtos.JMDictEntryDTO]:
        """
        Search entries by English meaning using full text search

        Args:
            query (str): The FTS5 match expression to run against glosses
            limit (int): Maximum number of entries to return

        Returns:
            The matching entries as data transfer objects
        """
        rows = self.session.execute(
            text(
                "SELECT s.entry_id FROM gloss_fts f "
                "JOIN jmdict_sense s ON s.id = f.sense_id "
                "WHERE gloss_fts MATCH :query LIMIT :limit"
            ),
            {"query": query, "limit": limit},
        )
        unique: dict[int, None] = {}
        for (entry_id,) in rows:
            unique.setdefault(entry_id, None)
        return self._by_ids(list(unique))


# --- JMnedict ---
_JMNEDICT_LOAD = (
    selectinload(JMnedictEntry.kanji),
    selectinload(JMnedictEntry.kana),
    selectinload(JMnedictEntry.translations).selectinload(
        JMnedictTranslation.glosses
    ),
)
"""
Eager-loading configuration for `JMNedict` entries
"""


class JMNeDictRepo(Repository):
    """
    Queries the JMnedict tables
    """

    def by_id(self, entry_id: int) -> dtos.JMNeDictEntryDTO | None:
        """
        Fetch a single name entry by its sequence number

        Args:
            entry_id (int): The JMnedict sequence number

        Returns:
            The entry, or None when no entry has that id
        """
        entry = self.session.get(
            JMnedictEntry, entry_id, options=_JMNEDICT_LOAD
        )
        return dtos.JMNeDictEntryDTO.from_orm(entry) if entry else None

    def search(
        self,
        form: str,
        *,
        wildcard: bool = False,
        limit: int | None = 50,
    ) -> list[dtos.JMNeDictEntryDTO]:
        """
        Search names by a written or reading form

        Args:
            form (str): The query form, where `*` and `%` act as wildcards when
                `wildcard` is True
            wildcard (bool): When True, treat the query as a `LIKE` pattern,
                otherwise match it exactly
            limit (int | None): Maximum entries to return, or None for no limit

        Returns:
            The matching names as data transfer objects
        """
        kanji_match: ColumnElement[bool]
        kana_match: ColumnElement[bool]
        if wildcard:
            pattern = form.replace("*", "%")
            kanji_match = JMnedictKanji.text.like(pattern)
            kana_match = JMnedictKana.text.like(pattern)
        else:
            kanji_match = JMnedictKanji.text == form
            kana_match = JMnedictKana.text == form
        statement = (
            select(JMnedictEntry)
            .where(
                JMnedictEntry.kanji.any(kanji_match)
                | JMnedictEntry.kana.any(kana_match)
            )
            .options(*_JMNEDICT_LOAD)
            .order_by(JMnedictEntry.id)
            .limit(limit)
        )
        entries = self.session.scalars(statement).all()
        return [dtos.JMNeDictEntryDTO.from_orm(entry) for entry in entries]

    def browse_by_type(
        self,
        name_type: str,
        *,
        limit: int = 50,
    ) -> list[dtos.JMNeDictEntryDTO]:
        """
        Browse names that carry a given name type

        Args:
            name_type (str): The name type code such as `place` or `surname`
            limit (int): Maximum number of entries to return

        Returns:
            The matching names as data transfer objects
        """
        entry_ids = self.session.scalars(
            select(JMnedictTranslation.entry_id)
            .where(JMnedictTranslation.name_type.like(f'%"{name_type}"%'))
            .distinct()
            .limit(limit)
        ).all()
        if not entry_ids:
            return []
        entries = self.session.scalars(
            select(JMnedictEntry)
            .where(JMnedictEntry.id.in_(list(entry_ids)))
            .options(*_JMNEDICT_LOAD)
            .order_by(JMnedictEntry.id)
        ).all()
        return [dtos.JMNeDictEntryDTO.from_orm(entry) for entry in entries]


# --- Kanji ---
_KANJI_LOAD = (
    selectinload(Kanji.readings),
    selectinload(Kanji.meanings),
    selectinload(Kanji.nanori),
    selectinload(Kanji.dic_refs),
    selectinload(Kanji.query_codes),
    selectinload(Kanji.variants),
    selectinload(Kanji.codepoints),
    selectinload(Kanji.strokes),
)
"""
Eager-loading configuration for `kanji` entries
"""

_SVG_OPEN = (
    '<svg xmlns="http://www.w3.org/2000/svg"'
    ' xmlns:kvg="http://kanjivg.tagaini.net"'
    ' width="109" height="109" viewBox="0 0 109 109">'
    '<g fill="none" stroke="#000000" stroke-width="3"'
    ' stroke-linecap="round" stroke-linejoin="round">'
)
"""
Opening of a renderable KanjiVG document

KanjiVG draws every kanji on a 109 by 109 canvas and its `<path>` strokes carry
no styling, so this `<svg>` root supplies the namespace, the view box and a
default black stroke style. The style uses presentation attributes, which sit
at the bottom of the CSS cascade, so any consumer stylesheet can fully restyle
the strokes
"""

_SVG_CLOSE = "</g></svg>"
"""
Closing of a renderable KanjiVG document, matching `_SVG_OPEN`
"""


def _svg_document(fragment: str) -> str:
    """
    Wrap a raw KanjiVG `<kanji>` fragment into a renderable SVG document

    The stored markup is the raw `<kanji>` element, which is not an `<svg>` and
    carries no namespace or styling, so a browser renders nothing from it. The
    inner stroke groups and their `kvg` metadata are kept verbatim while an
    `<svg>` root supplies the SVG namespace, the `109` canvas view box and a
    default black stroke style that any consumer stylesheet can override

    Args:
        fragment (str): The serialized KanjiVG `<kanji>` element

    Returns:
        A standalone, browser renderable SVG document
    """
    start = fragment.index(">") + 1
    end = fragment.rindex("</kanji>")
    return f"{_SVG_OPEN}{fragment[start:end]}{_SVG_CLOSE}"


class KanjiRepo(Repository):
    """
    Queries KanjiDic2 together with radical and JLPT data
    """

    def _radicals(self, literals: Sequence[str]) -> dict[str, list[str]]:
        """
        Fetch radical components grouped by kanji

        Args:
            literals (Sequence[str]): The kanji to look up

        Returns:
            A mapping of kanji to its radical components
        """
        grouped: dict[str, list[str]] = {}
        if not literals:
            return grouped
        rows = self.session.execute(
            select(KanjiRadical.literal, KanjiRadical.radical).where(
                KanjiRadical.literal.in_(list(literals))
            )
        )
        for literal, radical in rows:
            grouped.setdefault(literal, []).append(radical)
        return grouped

    def _jlpt_levels(self, literals: Sequence[str]) -> dict[str, int]:
        """
        Fetch Tanos JLPT levels keyed by kanji

        Args:
            literals (Sequence[str]): The kanji to look up

        Returns:
            A mapping of kanji to its JLPT level
        """
        if not literals:
            return {}
        rows = self.session.execute(
            select(JlptKanji.kanji, JlptKanji.level).where(
                JlptKanji.kanji.in_(list(literals))
            )
        )
        return {row.kanji: row.level for row in rows}

    def by_literal(self, literal: str) -> dtos.KanjiDTO | None:
        """
        Fetch a single kanji with its full profile

        Args:
            literal (str): The kanji character

        Returns:
            The kanji, or None when it is not in the database
        """
        results = self.bulk_fetch([literal])
        return results[0] if results else None

    def bulk_fetch(self, literals: Sequence[str]) -> list[dtos.KanjiDTO]:
        """
        Fetch several kanji at once preserving input order

        Args:
            literals (Sequence[str]): The kanji characters to fetch

        Returns:
            The matching kanji as data transfer objects
        """
        ordered = list(dict.fromkeys(literals))
        if not ordered:
            return []
        rows = self.session.scalars(
            select(Kanji)
            .where(Kanji.literal.in_(ordered))
            .options(*_KANJI_LOAD)
        ).all()
        by_literal = {row.literal: row for row in rows}
        radicals = self._radicals(ordered)
        jlpt = self._jlpt_levels(ordered)
        result: list[dtos.KanjiDTO] = []
        for literal in ordered:
            kanji = by_literal.get(literal)
            if kanji is not None:
                result.append(
                    dtos.KanjiDTO.from_orm(
                        kanji,
                        radicals=radicals.get(literal, []),
                        jlpt_tanos=jlpt.get(literal),
                    )
                )
        return result

    def stroke_svg(self, literal: str, *, raw: bool = False) -> str | None:
        """
        Fetch a kanji's stroke order as SVG

        By default this returns a self-contained, browser renderable SVG
        document. Pass `raw` to get the original KanjiVG `<kanji>` fragment
        instead, which has no `<svg>` root or styling

        Args:
            literal (str): The kanji character
            raw (bool): When True, return the raw KanjiVG fragment unwrapped

        Returns:
            The stroke order SVG, or None when no stroke data exists
        """
        row = self.session.get(KanjiStrokes, literal)
        if row is None:
            return None
        return row.svg if raw else _svg_document(row.svg)

    def by_skip(self, code: str, *, limit: int = 100) -> list[dtos.KanjiDTO]:
        """
        Find kanji with a given SKIP query code

        Args:
            code (str): The SKIP code such as `1-4-3`
            limit (int): Maximum number of kanji to return

        Returns:
            The matching kanji as data transfer objects
        """
        literals = self.session.scalars(
            select(KanjiQueryCode.literal)
            .where(
                KanjiQueryCode.type == "skip",
                KanjiQueryCode.value == code,
            )
            .limit(limit)
        ).all()
        return self.bulk_fetch(list(literals))

    def search(
        self,
        *,
        stroke_count: int | None = None,
        grade: int | None = None,
        freq_max: int | None = None,
        jlpt: int | None = None,
        limit: int = 100,
    ) -> list[dtos.KanjiDTO]:
        """
        Search kanji by scalar attributes

        Args:
            stroke_count (int | None): Required stroke count
            grade (int | None): Required school grade
            freq_max (int | None): Maximum newspaper frequency rank
            jlpt (int | None): Required Tanos JLPT level
            limit (int): Maximum number of kanji to return

        Returns:
            The matching kanji, ordered by frequency then character
        """
        statement = select(Kanji.literal)
        if stroke_count is not None:
            statement = statement.where(Kanji.stroke_count == stroke_count)
        if grade is not None:
            statement = statement.where(Kanji.grade == grade)
        if freq_max is not None:
            statement = statement.where(
                Kanji.freq.is_not(None), Kanji.freq <= freq_max
            )
        if jlpt is not None:
            statement = statement.where(
                Kanji.literal.in_(
                    select(JlptKanji.kanji).where(JlptKanji.level == jlpt)
                )
            )
        statement = statement.order_by(
            Kanji.freq.is_(None), Kanji.freq, Kanji.literal
        ).limit(limit)
        literals = self.session.scalars(statement).all()
        return self.bulk_fetch(list(literals))


# --- Radicals ---
class RadicalRepo(Repository):
    """
    Queries radical data and performs radical search
    """

    def list_radicals(self) -> list[dtos.RadicalDTO]:
        """
        List every search radical with its stroke count

        Returns:
            The radicals ordered by stroke count then character
        """
        rows = self.session.scalars(
            select(Radical).order_by(Radical.stroke_count, Radical.radical)
        ).all()
        return [dtos.RadicalDTO.from_orm(row) for row in rows]

    def radicals_of(self, literal: str) -> list[str]:
        """
        List the radical components of a kanji

        Args:
            literal (str): The kanji character

        Returns:
            The radical components contained in the kanji
        """
        rows = self.session.execute(
            select(KanjiRadical.radical).where(KanjiRadical.literal == literal)
        )
        return [row.radical for row in rows]

    def kanji_by_radicals(self, radicals: Sequence[str]) -> list[str]:
        """
        Find kanji that contain every one of the given radicals

        Args:
            radicals (Sequence[str]): The radical components to require

        Returns:
            The kanji that contain all of the radicals
        """
        wanted = list(dict.fromkeys(radicals))
        if not wanted:
            return []
        statement = (
            select(KanjiRadical.literal)
            .where(KanjiRadical.radical.in_(wanted))
            .group_by(KanjiRadical.literal)
            .having(
                func.count(func.distinct(KanjiRadical.radical)) == len(wanted)
            )
        )
        return [literal for (literal,) in self.session.execute(statement)]


# --- Furigana ---
class FuriganaRepo(Repository):
    """
    Queries furigana segmentation
    """

    def for_text(
        self,
        text_value: str,
        reading: str | None = None,
    ) -> list[dtos.FuriganaDTO]:
        """
        Fetch furigana for a written form

        Args:
            text_value (str): The written spelling to look up
            reading (str | None): A specific reading to narrow the match

        Returns:
            The matching furigana segmentations
        """
        statement = select(Furigana).where(Furigana.text == text_value)
        if reading is not None:
            statement = statement.where(Furigana.reading == reading)
        rows = self.session.scalars(statement).all()
        return [dtos.FuriganaDTO.from_orm(row) for row in rows]


# --- Sentences ---
class SentenceRepo(Repository):
    """
    Queries Tatoeba example sentences and their translations
    """

    def search_containing(
        self,
        query: str,
        *,
        limit: int = 20,
        wildcard: bool = False,
    ) -> list[dtos.SentenceDTO]:
        """
        Find Japanese sentences containing the query text

        Args:
            query (str): The text to search for, where `*` and `%` act as
                wildcards when `wildcard` is True
            limit (int): Maximum number of sentences to return
            wildcard (bool): When True, treat the query as a `LIKE` pattern,
                otherwise match it as a substring

        Returns:
            The matching sentences with any aligned translations
        """
        pattern = query.replace("*", "%") if wildcard else f"%{query}%"
        sentences = self.session.scalars(
            select(Sentence)
            .where(Sentence.lang == "jpn", Sentence.text.like(pattern))
            .order_by(Sentence.id)
            .limit(limit)
        ).all()
        ids = [sentence.id for sentence in sentences]
        translations: dict[int, list[str]] = {}
        if ids:
            rows = self.session.execute(
                select(SentenceLink.source_id, Sentence.text)
                .join(Sentence, Sentence.id == SentenceLink.target_id)
                .where(SentenceLink.source_id.in_(ids))
            )
            for source_id, sentence_text in rows:
                translations.setdefault(source_id, []).append(sentence_text)
        return [
            dtos.SentenceDTO.from_orm(
                sentence,
                translations=translations.get(sentence.id, []),
            )
            for sentence in sentences
        ]


# --- JLPT ---
class JLPTRepo(Repository):
    """
    Queries the Tanos JLPT lists
    """

    def vocab_by_word(self, word: str) -> dtos.JLPTVocabDTO | None:
        """
        Find the JLPT vocabulary entry for a word

        Args:
            word (str): The headword or reading to look up

        Returns:
            The vocabulary entry, or None when the word is not listed
        """
        row = self.session.scalars(
            select(JlptVocab)
            .where((JlptVocab.word == word) | (JlptVocab.reading == word))
            .limit(1)
        ).first()
        return dtos.JLPTVocabDTO.from_orm(row) if row else None

    def kanji_levels(self, literals: Sequence[str]) -> dict[str, int]:
        """
        Map each given kanji to its JLPT level

        Args:
            literals (Sequence[str]): The kanji to look up

        Returns:
            A mapping of kanji to JLPT level for those that are listed
        """
        wanted = list(dict.fromkeys(literals))
        if not wanted:
            return {}
        rows = self.session.execute(
            select(JlptKanji.kanji, JlptKanji.level).where(
                JlptKanji.kanji.in_(wanted)
            )
        )
        return {row.kanji: row.level for row in rows}

    def grammar_like(
        self,
        query: str,
        *,
        limit: int = 20,
    ) -> list[dtos.JLPTGrammarDTO]:
        """
        Find JLPT grammar points whose text contains the query

        Args:
            query (str): The substring to search for in grammar points
            limit (int): Maximum number of grammar points to return

        Returns:
            The matching grammar points as data transfer objects
        """
        rows = self.session.scalars(
            select(JlptGrammar)
            .where(JlptGrammar.grammar.like(f"%{query}%"))
            .order_by(JlptGrammar.level.desc())
            .limit(limit)
        ).all()
        return [dtos.JLPTGrammarDTO.from_orm(row) for row in rows]

    def kanji_by_literal(self, literal: str) -> dtos.JLPTKanjiDTO | None:
        """
        Fetch the JLPT kanji entry for a literal

        Args:
            literal (str): The kanji character

        Returns:
            The JLPT kanji entry, or None when it is not listed
        """
        row = self.session.scalars(
            select(JlptKanji).where(JlptKanji.kanji == literal).limit(1)
        ).first()
        return dtos.JLPTKanjiDTO.from_orm(row) if row else None

    def list_vocab(self, level: int) -> list[dtos.JLPTVocabDTO]:
        """
        Return the full vocabulary study list for a level

        Args:
            level (int): The JLPT level from 1 to 5

        Returns:
            Every vocabulary item at the level
        """
        rows = self.session.scalars(
            select(JlptVocab)
            .where(JlptVocab.level == level)
            .order_by(JlptVocab.id)
        ).all()
        return [dtos.JLPTVocabDTO.from_orm(row) for row in rows]

    def list_kanji(self, level: int) -> list[dtos.JLPTKanjiDTO]:
        """
        Return the full kanji study list for a level

        Args:
            level (int): The JLPT level from 1 to 5

        Returns:
            Every kanji item at the level
        """
        rows = self.session.scalars(
            select(JlptKanji)
            .where(JlptKanji.level == level)
            .order_by(JlptKanji.id)
        ).all()
        return [dtos.JLPTKanjiDTO.from_orm(row) for row in rows]

    def list_grammar(self, level: int) -> list[dtos.JLPTGrammarDTO]:
        """
        Return the full grammar study list for a level

        Args:
            level (int): The JLPT level from 1 to 5

        Returns:
            Every grammar point at the level
        """
        rows = self.session.scalars(
            select(JlptGrammar)
            .where(JlptGrammar.level == level)
            .order_by(JlptGrammar.id)
        ).all()
        return [dtos.JLPTGrammarDTO.from_orm(row) for row in rows]


# --- Tags and audio ---
class TagRepo(Repository):
    """
    Queries the tag dictionary that expands codes to descriptions
    """

    def labels(self, codes: Sequence[str]) -> dict[str, str]:
        """
        Map tag codes to their human readable descriptions

        Args:
            codes (Sequence[str]): The tag codes to expand

        Returns:
            A mapping of code to description for those that are known
        """
        wanted = list(dict.fromkeys(codes))
        if not wanted:
            return {}
        rows = self.session.execute(
            select(Tag.code, Tag.description).where(Tag.code.in_(wanted))
        )
        return {row.code: row.description for row in rows}


_AUDIO_PACK_MISSING = (
    "Couldn't Find The Audio Database. Run "
    "`kotobase db pull --with-audio` Or "
    "`kotobase db build --with-audio` To Get It"
)
"""
Error message used when the optional audio pack is not attached
"""


class AudioRepo(Repository):
    """
    Queries pronunciation audio metadata and clips
    """

    def for_key(
        self,
        key: str,
        *,
        kind: str | None = None,
    ) -> list[dtos.AudioDTO]:
        """
        Fetch audio metadata for a lookup key

        Args:
            key (str): The lookup key, such as a kanji or word
            kind (str | None): Restrict to a clip kind when given

        Returns:
            The matching audio clips as metadata, without the raw bytes

        Raises:
            AudioDatabaseNotFoundError: If the optional audio pack is not
                installed
        """
        statement = select(Audio).where(Audio.key == key)
        if kind is not None:
            statement = statement.where(Audio.kind == kind)
        try:
            rows = self.session.scalars(statement).all()
        except OperationalError:
            self.session.rollback()
            raise AudioDatabaseNotFoundError(_AUDIO_PACK_MISSING) from None
        return [dtos.AudioDTO.from_orm(row) for row in rows]

    def payloads(
        self,
        key: str,
        *,
        reading: str | None = None,
        kind: str | None = None,
    ) -> list[tuple[str, bytes]]:
        """
        Fetch the file name and raw bytes of each matching audio clip

        Args:
            key (str): The lookup key, such as a kanji or word
            reading (str | None): Restrict to a single clip reading when given
            kind (str | None): Restrict to a clip kind when given

        Returns:
            A file name and bytes pair for every bundled clip that matches

        Raises:
            AudioDatabaseNotFoundError: If the optional audio pack is not
                installed
        """
        statement = select(Audio).where(Audio.key == key)
        if reading is not None:
            statement = statement.where(Audio.reading == reading)
        if kind is not None:
            statement = statement.where(Audio.kind == kind)
        try:
            rows = self.session.scalars(statement).all()
        except OperationalError:
            self.session.rollback()
            raise AudioDatabaseNotFoundError(_AUDIO_PACK_MISSING) from None
        result: list[tuple[str, bytes]] = []
        for row in rows:
            if row.data is None:
                continue
            name = f"{row.reading or key}.{row.fmt or 'mp3'}"
            result.append((name, row.data))
        return result
