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

info: Error Handling
    - Every repository inherits from
      [`KotobaseRepo`][kotobase.db.repos.KotobaseRepo], whose
      `__init_subclass__` wraps each public method so an unexpected
      `SQLAlchemy` failure surfaces as a
      [`DatabaseError`][kotobase.exceptions.DatabaseError]

    - Kotobase errors, such as a missing audio pack, pass through unchanged
"""

from __future__ import annotations

import functools
from collections.abc import Callable, Sequence
from typing import Any, ParamSpec, TypeVar

from sqlalchemy import ColumnElement, func, select, text
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from ..exceptions import (
    AudioDatabaseNotFoundError,
    DatabaseError,
    KotobaseError,
)
from . import dtos
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

# --- Typing Helpers ---

_P = ParamSpec("_P")
_R = TypeVar("_R")
_T = TypeVar("_T", bound=type)

# --- Eager Loading Helpers ---
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

_JMDICT_LOAD = (
    selectinload(JMDictEntry.kanji),
    selectinload(JMDictEntry.kana),
    selectinload(JMDictEntry.senses).selectinload(JMDictSense.glosses),
)
"""
Eager-loading configuration for `JMdict` entries
"""

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

# --- Ordering Helpers ---

_JMDICT_ORDER = (
    JMDictEntry.is_common.desc(),
    JMDictEntry.freq_rank.is_(None),
    JMDictEntry.freq_rank,
    JMDictEntry.id,
)
"""
Defines the default sorting priority for JMDict vocabulary entries

info: `Common` Entries
    Kotobase classifies a `JMDict` entry's kanji / kana form as being
    `common` when it contains any of the following priority codes in its
    JMDict XML `<pri>` Tags

    - `news1`
    - `ichi1`
    - `spec1`
    - `spec2`
    - `gai1`

This ordering configuration ensures that search results are intuitive,
relevant, and deterministic by applying a four-tiered sorting logic

info: `1` - Commonality (`JMDictEntry.is_common.desc()`)
   Prioritizes entry records marked as common over rare or archaic terms

info: `2` - Null Frequency Handling (`JMDictEntry.freq_rank.is_(None)`)
   - Acts as a data-integrity guard rail

   - In `SQL`, boolean expressions evaluate to 0 (False) or 1 (True). By
     sorting ascending, entries *with* frequency data (False/0) are grouped
     ahead of entries *without* frequency data (True/1)

   - This prevents `NULL` values from breaking or misaligning the subsequent
     numerical sort

info: `3` - Frequency Rank (`JMDictEntry.freq_rank`)
   - Sorts entries numerically by their popularity rank

   - Lower numbers represent higher real-world usage
     (e.g. A rank of 50 appears before a rank of 5000)

info: `4` -  Primary Key Determinism (`JMDictEntry.id`)
   - Serves as the absolute tie-breaker using the entry's unique ID

   - This guarantees a stable, identical sorting order across identical data
     subsets, which is essential for consistent pagination and preventing
     duplicate items across page loads
"""

# --- SVG Helpers ---

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


# --- Exception Handling Helpers ---


def _wrap_sqlalchemy_error(method: Callable[_P, _R]) -> Callable[_P, _R]:
    """
    Decorates a repository method so a raised `SQLAlchemyError` becomes a
    [`DatabaseError`][kotobase.exceptions.DatabaseError]

    The returned wrapper calls `method` and lets its result pass through. A
    [`KotobaseError`][kotobase.exceptions.KotobaseError] is re-raised unchanged
    so callers can still distinguish it. Any other `SQLAlchemyError` is
    re-raised as a `DatabaseError` whose message names the failing method via
    its `__qualname__` and chains the original exception with `from`.
    The wrapper keeps the wrapped method's identity through `functools.wraps`

    Args:
        method (Callable[_P, _R]): The repository method to wrap

    Returns:
        The wrapped method, with the same signature and return type
    """

    @functools.wraps(method)
    def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _R:
        try:
            return method(*args, **kwargs)
        except KotobaseError:
            raise
        except SQLAlchemyError as exc:
            raise DatabaseError(
                f"Database Query Failed In '{method.__qualname__}' : {exc}"
            ) from exc

    return wrapper


# --- Base Repository Class ---


class KotobaseRepo:
    """
    Base class for a repository that runs queries through one shared session

    info: Error Handling
        - Subclassing also installs the central error wrapping

        - Every public method a subclass defines is replaced with a version
          that converts a raised `SQLAlchemyError` into a
          [`DatabaseError`][kotobase.exceptions.DatabaseError], so individual
          methods only document their own non-`SQLAlchemy` raises

    Attributes:
        session (Session): The session, owned by the unit of work, that every
            query on this repository runs through
    """

    def __init__(self, session: Session) -> None:
        """
        Store the session this repository runs all of its queries through

        The session is not opened or owned here, it is supplied by the unit of
        work and shared with the other repositories

        Args:
            session (Session): The active session to query through
        """
        self.session = session

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """
        Wrap each public method the subclass defines with the `SQLAlchemy`
        error handler

        Iterates the subclass's own `vars`, and for every callable, non-`_`
        attribute, replaces it with the result of `_wrap_sqlalchemy_error`, so
        a raised `SQLAlchemyError` surfaces as a
        [`DatabaseError`][kotobase.exceptions.DatabaseError] while a
        [`KotobaseError`][kotobase.exceptions.KotobaseError] passes through

        Args:
            **kwargs (Any): Extra arguments forwarded to the base hook
        """
        super().__init_subclass__(**kwargs)

        for name, attr in list(vars(cls).items()):
            if not name.startswith("_") and callable(attr):
                setattr(cls, name, _wrap_sqlalchemy_error(attr))


class JMDictRepo(KotobaseRepo):
    """
    Repository that abstracts queries over the `JMdict` tables

    Looks up entries by sequence number, by written or reading form against the
    normalized `jmdict_kanji` / `jmdict_kana` tables, and by English meaning
    through the `gloss_fts` full-text index. Every method eagerly loads kanji
    forms, kana forms and senses with their glosses (`_JMDICT_LOAD`) and
    returns [`JMDictEntryDTO`][kotobase.db.dtos.JMDictEntryDTO] objects built
    with `model_validate`
    """

    def by_id(self, entry_id: int) -> dtos.JMDictEntryDTO | None:
        """
        Fetch one entry by its `JMdict` sequence number

        Loads the row through `Session.get` with `_JMDICT_LOAD` eager loading
        of its kanji forms, kana forms and senses with glosses, then validates
        it into a [`JMDictEntryDTO`][kotobase.db.dtos.JMDictEntryDTO]

        Args:
            entry_id (int): The `JMdict` sequence number (primary key)

        Returns:
            The entry as a DTO, or `None` when no row has that id
        """
        entry = self.session.get(JMDictEntry, entry_id, options=_JMDICT_LOAD)
        return dtos.JMDictEntryDTO.model_validate(entry) if entry else None

    def _by_ids(self, ids: list[int]) -> list[dtos.JMDictEntryDTO]:
        """
        Fetch several entries by id in the canonical `JMdict` order

        Selects every [`JMDictEntry`][kotobase.db.models.JMDictEntry] whose id
        is `IN` the given list, eager-loading with `_JMDICT_LOAD` and ordering
        by `_JMDCIT_ORDER`
        Args:
            ids (list[int]): The entry ids to fetch

        Returns:
            The matching entries as DTOs ordered by commonness then frequency,
                or `[]` when `ids` is empty
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
        return [dtos.JMDictEntryDTO.model_validate(entry) for entry in entries]

    def search_form(
        self,
        form: str,
        *,
        wildcard: bool = False,
        limit: int | None = 50,
    ) -> list[dtos.JMDictEntryDTO]:
        """
        Search entries by a written or reading form

        Matches `form` against `JMDictKanji.text` or `JMDictKana.text` using
        `EXISTS` (`relationship.any`). By default the comparison is exact. When
        `wildcard` is True, `*` is translated to `%` and the form is matched as
        a SQL `LIKE` pattern. Results are eager-loaded with
        `_JMDICT_LOAD`, ordered by `_JMDICT_ORDER`, and capped at `limit`

        Args:
            form (str): The query form, where `*` and `%` act as wildcards when
                `wildcard` is True
            wildcard (bool): When True, treat the query as a `LIKE` pattern,
                otherwise match it exactly
            limit (int | None): Maximum entries to return, or `None` for no
                limit

        Returns:
            The matching entries as DTOs, or `[]` when none match
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
        return [dtos.JMDictEntryDTO.model_validate(entry) for entry in entries]

    def search_gloss(
        self,
        query: str,
        *,
        limit: int | None = 50,
    ) -> list[dtos.JMDictEntryDTO]:
        """
        Search entries by English meaning through the `gloss_fts` index

        Runs a raw `FTS5` query that matches `query` against the `gloss_fts`
        virtual table (`gloss_fts MATCH :query`), joined to `jmdict_sense` to
        recover each matching sense's `entry_id`, capped at `limit` rows. The
        entry ids are de-duplicated while preserving first-seen order, then
        re-fetched and ordered through `_by_ids`, so the final ordering is the
        canonical commonness/frequency order rather than relevance

        Args:
            query (str): The `FTS5` match expression to run against glosses
            limit (int | None): Maximum number of `gloss_fts` rows to scan

        Returns:
            The matching entries as DTOs, or `[]` when none match
        """
        rows = self.session.execute(
            text(
                "SELECT s.entry_id FROM gloss_fts f "
                "JOIN jmdict_sense s ON s.id = f.sense_id "
                "WHERE gloss_fts MATCH :query LIMIT :limit"
            ),
            {"query": query, "limit": -1 if limit is None else limit},
        )
        unique: dict[int, None] = {}
        for (entry_id,) in rows:
            unique.setdefault(entry_id, None)
        return self._by_ids(list(unique))

    def resolve_reference(self, ref: str) -> list[dtos.JMDictEntryDTO]:
        """
        Resolve a cross-reference or antonym code to its entries

        `JMdict` `xref` and `antonym` codes are `・`-separated into a leading
        form and an optional disambiguating reading and sense number. This
        takes the part before the first `・`, strips it, and when it is
        non-empty looks it up exactly through `search_form` with no limit (the
        reading and sense number are ignored). An empty leading form returns
        `[]` without querying

        Args:
            ref (str): The cross-reference or antonym code to resolve

        Returns:
            The entries the leading form points to, or `[]` when the form is
                empty or nothing matches
        """
        form = ref.split("・")[0].strip()
        if not form:
            return []
        return self.search_form(form, limit=None)


# --- JMnedict ---


class JMNeDictRepo(KotobaseRepo):
    """
    Repository that abstracts queries over the `JMnedict` proper-name tables

    Looks up names by sequence number, by written or reading form against the
    normalized `jmnedict_kanji` / `jmnedict_kana` tables, and by name type.
    Every method eagerly loads kanji forms, kana forms and translation blocks
    with their glosses (`_JMNEDICT_LOAD`) and returns
    [`JMNeDictEntryDTO`][kotobase.db.dtos.JMNeDictEntryDTO] objects built with
    `model_validate`
    """

    def by_id(self, entry_id: int) -> dtos.JMNeDictEntryDTO | None:
        """
        Fetch one name entry by its `JMnedict` sequence number

        Loads the row through `Session.get` with `_JMNEDICT_LOAD` eager loading
        of its kanji forms, kana forms and translation blocks with glosses,
        then validates it into a
        [`JMNeDictEntryDTO`][kotobase.db.dtos.JMNeDictEntryDTO]

        Args:
            entry_id (int): The `JMnedict` sequence number (primary key)

        Returns:
            The name entry as a DTO, or `None` when no row has that id
        """
        entry = self.session.get(
            JMnedictEntry, entry_id, options=_JMNEDICT_LOAD
        )
        return dtos.JMNeDictEntryDTO.model_validate(entry) if entry else None

    def search(
        self,
        form: str,
        *,
        wildcard: bool = False,
        limit: int | None = 50,
    ) -> list[dtos.JMNeDictEntryDTO]:
        """
        Search names by a written or reading form

        Matches `form` against `JMnedictKanji.text` or `JMnedictKana.text`
        with `EXISTS` (`relationship.any`). By default the comparison is exact.
        When `wildcard` is True, `*` is translated to `%` and the form
        is matched as a SQL `LIKE` pattern. Results are eager-loaded with
        `_JMNEDICT_LOAD`, ordered by ascending `JMnedictEntry.id` and capped at
        `limit`

        Args:
            form (str): The query form, where `*` and `%` act as wildcards when
                `wildcard` is True
            wildcard (bool): When True, treat the query as a `LIKE` pattern,
                otherwise match it exactly
            limit (int | None): Maximum entries to return, or `None` for no
                limit

        Returns:
            The matching names as DTOs ordered by id, or `[]` when none match
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
        return [
            dtos.JMNeDictEntryDTO.model_validate(entry) for entry in entries
        ]

    def browse_by_type(
        self,
        name_type: str,
        *,
        limit: int | None = 50,
    ) -> list[dtos.JMNeDictEntryDTO]:
        """
        Browse names that carry a given name type

        The `name_type` codes of a block are stored as a JSON list in
        `JMnedictTranslation.name_type`, so this matches the quoted code as a
        substring (`LIKE '%"<name_type>"%'`) to find translation blocks of that
        type, collecting up to `limit` distinct owning `entry_id` values. Those
        entries are then re-fetched eager-loaded with `_JMNEDICT_LOAD` and
        ordered by ascending id. When no block matches, returns `[]` without
        the second query

        Args:
            name_type (str): The name type code such as `place` or `surname`
            limit (int | None): Maximum number of distinct entry ids to collect

        Returns:
            The matching names as DTOs ordered by id, or `[]` when none match
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
        return [
            dtos.JMNeDictEntryDTO.model_validate(entry) for entry in entries
        ]


# --- Kanji ---


def _svg_document(fragment: str) -> str:
    """
    Wrap a raw KanjiVG `<kanji>` fragment into a renderable SVG document

    The stored markup is the raw `<kanji>` element, which is not an `<svg>` and
    carries no namespace or styling, so a browser renders nothing from it. This
    slices out the element's inner content, the stroke `<g>` groups and their
    `kvg` metadata, between the end of the opening `<kanji ...>` tag (the first
    `>`) and the final `</kanji>`, then splices it between `_SVG_OPEN` and
    `_SVG_CLOSE`, which add the SVG namespace, the 109 canvas view box and a
    default black stroke style that any consumer stylesheet can override

    Args:
        fragment (str): The serialized KanjiVG `<kanji>` element

    Returns:
        A standalone, browser renderable SVG document
    """
    start = fragment.index(">") + 1
    end = fragment.rindex("</kanji>")
    return f"{_SVG_OPEN}{fragment[start:end]}{_SVG_CLOSE}"


def _kanji_payload(
    kanji: Kanji,
    radicals: Sequence[str],
    jlpt_tanos: int | None,
) -> dict[str, Any]:
    """
    Assemble a `KanjiDTO`-ready mapping from a loaded kanji ORM row

    Flattens the kanji's relationships into the shapes
    [`KanjiDTO`][kotobase.db.dtos.KanjiDTO] expects, since they cannot be
    mapped field-for-field

    info: Formatting

    - The `readings` relationship is split by `type` into `onyomi` (`ja_on`),
      `kunyomi` (`ja_kun`), `pinyin` and `korean` (`korean_r` / `korean_h`)

    - `meanings` is filtered to English (`lang == "en"`)

    - `query_codes` is grouped into a `type -> [value]` dict while
      `dic_refs` and `codepoints` become `type -> value` dicts

    - `variants` keeps its `type` / `value` pairs

    - `has_stroke_order` is True when the `strokes` relationship is present

    - The `radicals` and `jlpt_tanos` values, which are not kanji
      relationships, are passed in by the caller and overlaid

    Args:
        kanji (Kanji): The kanji with its readings, meanings, nanori, dic refs,
            query codes, variants, codepoints and stroke data loaded
        radicals (Sequence[str]): Radical components, passed in since they are
            not a direct relationship of the kanji
        jlpt_tanos (int | None): The Tanos JLPT level when known

    Returns:
        A mapping with the derived list and dict fields `KanjiDTO` expects
    """
    query_codes: dict[str, list[str]] = {}
    for code in kanji.query_codes:
        query_codes.setdefault(code.type, []).append(code.value)
    korean = ("korean_r", "korean_h")
    return {
        "literal": kanji.literal,
        "grade": kanji.grade,
        "stroke_count": kanji.stroke_count,
        "freq": kanji.freq,
        "jlpt_old": kanji.jlpt_old,
        "jlpt_tanos": jlpt_tanos,
        "onyomi": [r.value for r in kanji.readings if r.type == "ja_on"],
        "kunyomi": [r.value for r in kanji.readings if r.type == "ja_kun"],
        "nanori": [n.value for n in kanji.nanori],
        "pinyin": [r.value for r in kanji.readings if r.type == "pinyin"],
        "korean": [r.value for r in kanji.readings if r.type in korean],
        "meanings": [m.value for m in kanji.meanings if m.lang == "en"],
        "radicals": list(radicals),
        "dic_refs": {ref.type: ref.value for ref in kanji.dic_refs},
        "query_codes": query_codes,
        "codepoints": {cp.type: cp.value for cp in kanji.codepoints},
        "variants": [
            {"type": v.type, "value": v.value} for v in kanji.variants
        ],
        "has_stroke_order": kanji.strokes is not None,
    }


class KanjiRepo(KotobaseRepo):
    """
    Repository that abstracts `KanjiDic2` lookups enriched with extras

    Reads kanji from the `kanji` table, eager-loading every per-character
    relationship, and joins in two pieces that
    are not kanji relationships, the `KRADFILE` radical components and the
    Tanos JLPT level, which are injected through `_kanji_payload` when
    validating each [`KanjiDTO`][kotobase.db.dtos.KanjiDTO]. Also serves
    stroke-order SVG and lookups by SKIP code or scalar attribute
    """

    def _radicals(self, literals: Sequence[str]) -> dict[str, list[str]]:
        """
        Fetch the `KRADFILE` radical components grouped by kanji

        Selects `(literal, radical)` rows from
        [`KanjiRadical`][kotobase.db.models.KanjiRadical] whose `literal` is
        `IN` the given set and groups the radicals under each kanji. An empty
        `literals` argument returns `{}` without a query

        Args:
            literals (Sequence[str]): The kanji to look up

        Returns:
            A mapping of each kanji to its list of radical components, omitting
                kanji that have no rows
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

        Selects `(kanji, level)` rows from
        [`JlptKanji`][kotobase.db.models.JlptKanji] whose `kanji` is `IN` the
        given set. An empty `literals` argument returns `{}` without a query

        Args:
            literals (Sequence[str]): The kanji to look up

        Returns:
            A mapping of each listed kanji to its Tanos JLPT level, omitting
                kanji that are not in the Tanos list
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
        Fetch one kanji with its full profile

        Thin wrapper that delegates to `bulk_fetch` with a single literal and
        unwraps the result

        Args:
            literal (str): The kanji character

        Returns:
            The kanji as a [`KanjiDTO`][kotobase.db.dtos.KanjiDTO], or `None`
                when the character is not in the `kanji` table
        """
        results = self.bulk_fetch([literal])
        return results[0] if results else None

    def bulk_fetch(self, literals: Sequence[str]) -> list[dtos.KanjiDTO]:
        """
        Fetch several kanji at once, preserving first-seen input order

        De-duplicates `literals` while keeping order, then selects the matching
        [`Kanji`][kotobase.db.models.Kanji] rows (`literal IN ...`)
        eager-loaded with `_KANJI_LOAD`, and gathers their radical components
        and Tanos JLPT levels through `_radicals` and `_jlpt_levels`. Each
        found kanji is built into a [`KanjiDTO`][kotobase.db.dtos.KanjiDTO] via
        `_kanji_payload`, which injects that kanji's radicals and JLPT level,
        and the results are emitted in input order. Requested literals with no
        `kanji` row are skipped, so the result may be shorter than the input.
        An empty input returns `[]` without a query

        Args:
            literals (Sequence[str]): The kanji characters to fetch

        Returns:
            The matching kanji as DTOs in input order, or `[]` when none match
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
                    dtos.KanjiDTO.model_validate(
                        _kanji_payload(
                            kanji,
                            radicals.get(literal, []),
                            jlpt.get(literal),
                        )
                    )
                )
        return result

    def stroke_svg(self, literal: str, *, raw: bool = False) -> str | None:
        """
        Fetch a kanji's KanjiVG stroke order as SVG

        Loads the [`KanjiStrokes`][kotobase.db.models.KanjiStrokes] row by its
        `literal` primary key. By default the stored KanjiVG `<kanji>` markup
        is wrapped through `_svg_document` into a self-contained, browser
        renderable `<svg>` document. Pass `raw` to get that stored `<kanji>`
        fragment verbatim instead, which has no `<svg>` root or styling

        Args:
            literal (str): The kanji character
            raw (bool): When True, return the raw KanjiVG fragment unwrapped

        Returns:
            The stroke order SVG, or `None` when the kanji has no stroke row
        """
        row = self.session.get(KanjiStrokes, literal)
        if row is None:
            return None
        return row.svg if raw else _svg_document(row.svg)

    def by_skip(
        self,
        code: str,
        *,
        limit: int | None = 100,
    ) -> list[dtos.KanjiDTO]:
        """
        Find kanji with a given SKIP query code

        Selects up to `limit` `literal` values from
        [`KanjiQueryCode`][kotobase.db.models.KanjiQueryCode] where `type` is
        `skip` and `value` equals `code` exactly, then re-fetches their full
        profiles through `bulk_fetch`

        Args:
            code (str): The SKIP code such as `1-4-3`
            limit (int | None): Maximum number of matching literals to collect

        Returns:
            The matching kanji as DTOs, or `[]` when none carry the code
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
        limit: int | None = 100,
    ) -> list[dtos.KanjiDTO]:
        """
        Search kanji by scalar attributes

        Builds a `select` over `Kanji.literal`, adding a filter for each
        non-`None` argument. The literals are ordered with kanji
        that have a `freq` ahead of those without, then by ascending `freq`,
        then by character, capped at `limit`, and re-fetched as full profiles
        through `bulk_fetch`

        info: Filters
            - `stroke_count` and `grade` match exactly
            - `freq_max` keeps only kanji whose `freq` is set and `<= freq_max`
            - `jlpt` restricts to literals present in
            [`JlptKanji`][kotobase.db.models.JlptKanji] at that level
              (subquery)

            - Omitted arguments add no filter

        Args:
            stroke_count (int | None): Required exact stroke count
            grade (int | None): Required exact school grade
            freq_max (int | None): Maximum newspaper frequency rank
            jlpt (int | None): Required Tanos JLPT level
            limit (int | None): Maximum number of matching literals to collect

        Returns:
            The matching kanji as DTOs, ordered by frequency then character, or
                `[]` when none match
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
class RadicalRepo(KotobaseRepo):
    """
    Repository for the `RADKFILE` / `KRADFILE` radical decomposition data

    Lists the `RADKFILE` search radicals, reads a kanji's radical components,
    and performs reverse radical search, finding the kanji that contain a
    chosen set of radicals
    """

    def list_radicals(self) -> list[dtos.RadicalDTO]:
        """
        List every `RADKFILE` search radical with its stroke count

        Selects all [`Radical`][kotobase.db.models.Radical] rows ordered by
        ascending `stroke_count` then radical character, and validates each
        into a [`RadicalDTO`][kotobase.db.dtos.RadicalDTO]

        Returns:
            Every search radical as a DTO, ordered by stroke count then
                character
        """
        rows = self.session.scalars(
            select(Radical).order_by(Radical.stroke_count, Radical.radical)
        ).all()
        return [dtos.RadicalDTO.model_validate(row) for row in rows]

    def radicals_of(self, literal: str) -> list[str]:
        """
        List the `KRADFILE` radical components of one kanji

        Selects the `radical` column from
        [`KanjiRadical`][kotobase.db.models.KanjiRadical] for rows whose
        `literal` equals the kanji exactly, in primary-key order

        Args:
            literal (str): The kanji character

        Returns:
            The radical components contained in the kanji, or `[]` when the
                kanji has no decomposition
        """
        rows = self.session.execute(
            select(KanjiRadical.radical).where(KanjiRadical.literal == literal)
        )
        return [row.radical for row in rows]

    def kanji_by_radicals(
        self,
        radicals: Sequence[str],
        *,
        match: str = "all",
    ) -> list[str]:
        """
        Find kanji that contain the given radicals (reverse radical search)

        De-duplicates `radicals`, then groups
        [`KanjiRadical`][kotobase.db.models.KanjiRadical] rows whose `radical`
        is `IN` that set by `literal`. With `match="all"` a `HAVING` clause
        keeps only kanji whose distinct matched-radical count equals the number
        of requested radicals, so every radical is required (intersection). Any
        other `match` value (such as `"any"`) drops the `HAVING` clause, so a
        kanji that contains at least one of the radicals matches (union). An
        empty `radicals` argument returns `[]` without a query

        Args:
            radicals (Sequence[str]): The radical components to match against
            match (str): `all` to require every radical (intersection), or
                `any` to match kanji that contain at least one (union)

        Returns:
            The matching kanji literals, or `[]` when none match
        """
        wanted = list(dict.fromkeys(radicals))
        if not wanted:
            return []
        statement = (
            select(KanjiRadical.literal)
            .where(KanjiRadical.radical.in_(wanted))
            .group_by(KanjiRadical.literal)
        )
        if match == "all":
            statement = statement.having(
                func.count(func.distinct(KanjiRadical.radical)) == len(wanted)
            )
        return [literal for (literal,) in self.session.execute(statement)]


# --- Furigana ---
class FuriganaRepo(KotobaseRepo):
    """
    Repository for `JmdictFurigana` spelling-to-reading segmentation
    """

    def for_text(
        self,
        text_value: str,
        reading: str | None = None,
    ) -> list[dtos.FuriganaDTO]:
        """
        Fetch furigana segmentations for a written form

        Selects [`Furigana`][kotobase.db.models.Furigana] rows whose `text`
        equals `text_value` exactly. When `reading` is given it is added as a
        second exact-match filter on `Furigana.reading`, narrowing to the one
        spelling/reading pair (which is unique). Each row is validated into a
        [`FuriganaDTO`][kotobase.db.dtos.FuriganaDTO]

        Args:
            text_value (str): The written spelling to look up
            reading (str | None): A specific reading to narrow the match

        Returns:
            The matching furigana segmentations as DTOs, or `[]` when none
                match
        """
        statement = select(Furigana).where(Furigana.text == text_value)
        if reading is not None:
            statement = statement.where(Furigana.reading == reading)
        rows = self.session.scalars(statement).all()
        return [dtos.FuriganaDTO.model_validate(row) for row in rows]


# --- Sentences ---
class SentenceRepo(KotobaseRepo):
    """
    Repository for `Tatoeba` example sentences and their translations
    """

    def search_containing(
        self,
        query: str,
        *,
        limit: int | None = 20,
        wildcard: bool = False,
    ) -> list[dtos.SentenceDTO]:
        """
        Find Japanese sentences containing the query text, with translations

        Selects up to `limit` [`Sentence`][kotobase.db.models.Sentence] rows
        where `lang` is `jpn` and `text` matches a SQL `LIKE` pattern, ordered
        by ascending id. By default the query is wrapped as `%query%` substring
        containment. When `wildcard` is True, `*` is translated to `%` and the
        query is used as the `LIKE` pattern directly. For the matched sentences
        it then resolves translations by joining
        [`SentenceLink`][kotobase.db.models.SentenceLink] (whose `source_id` is
        the Japanese sentence) to the target `Sentence.text`, grouping the
        translation texts per source id. Each sentence is validated into a
        [`SentenceDTO`][kotobase.db.dtos.SentenceDTO] with its translations
        injected through the validation `context`

        Args:
            query (str): The text to search for, where `*` and `%` act as
                wildcards when `wildcard` is True
            limit (int | None): Maximum number of sentences to return
            wildcard (bool): When True, treat the query as a `LIKE` pattern,
                otherwise match it as a `%query%` substring

        Returns:
            The matching sentences as DTOs with their aligned translations, or
                `[]` when none match
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
            dtos.SentenceDTO.model_validate(
                sentence,
                context={"translations": translations.get(sentence.id, [])},
            )
            for sentence in sentences
        ]


# --- JLPT ---
class JLPTRepo(KotobaseRepo):
    """
    Repository for the Tanos JLPT vocabulary, kanji and grammar lists

    Resolves a word or kanji to its JLPT level, searches grammar points by
    substring, and returns full per-level study lists. Each method validates
    rows into the matching JLPT DTO
    """

    def vocab_by_word(self, word: str) -> dtos.JLPTVocabDTO | None:
        """
        Find the JLPT vocabulary entry for a word or reading

        Selects the first [`JlptVocab`][kotobase.db.models.JlptVocab] row whose
        `word` or `reading` equals `word` exactly (`LIMIT 1`), and validates it
        into a [`JLPTVocabDTO`][kotobase.db.dtos.JLPTVocabDTO]

        Args:
            word (str): The headword or reading to look up

        Returns:
            The vocabulary entry as a DTO, or `None` when the word is not
                listed
        """
        row = self.session.scalars(
            select(JlptVocab)
            .where((JlptVocab.word == word) | (JlptVocab.reading == word))
            .limit(1)
        ).first()
        return dtos.JLPTVocabDTO.model_validate(row) if row else None

    def kanji_levels(self, literals: Sequence[str]) -> dict[str, int]:
        """
        Map each given kanji to its Tanos JLPT level

        De-duplicates `literals`, then selects `(kanji, level)` from
        [`JlptKanji`][kotobase.db.models.JlptKanji] where `kanji` is `IN` that
        set. An empty input returns `{}` without a query

        Args:
            literals (Sequence[str]): The kanji to look up

        Returns:
            A mapping of each listed kanji to its JLPT level, omitting kanji
                not in the Tanos list
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
        limit: int | None = 20,
    ) -> list[dtos.JLPTGrammarDTO]:
        """
        Find JLPT grammar points whose text contains the query

        Selects up to `limit` [`JlptGrammar`][kotobase.db.models.JlptGrammar]
        rows whose `grammar` contains `query` as a substring
        (`LIKE '%query%'`), ordered by descending `level` (so N1 grammar comes
        before N5), and validates each into a
        [`JLPTGrammarDTO`][kotobase.db.dtos.JLPTGrammarDTO]

        Args:
            query (str): The substring to search for in grammar points
            limit (int | None): Maximum number of grammar points to return

        Returns:
            The matching grammar points as DTOs ordered by descending level, or
                `[]` when none match
        """
        rows = self.session.scalars(
            select(JlptGrammar)
            .where(JlptGrammar.grammar.like(f"%{query}%"))
            .order_by(JlptGrammar.level.desc())
            .limit(limit)
        ).all()
        return [dtos.JLPTGrammarDTO.model_validate(row) for row in rows]

    def kanji_by_literal(self, literal: str) -> dtos.JLPTKanjiDTO | None:
        """
        Fetch the JLPT kanji entry for a literal

        Selects the first [`JlptKanji`][kotobase.db.models.JlptKanji] row whose
        `kanji` equals `literal` exactly (`LIMIT 1`) and validates it into a
        [`JLPTKanjiDTO`][kotobase.db.dtos.JLPTKanjiDTO]

        Args:
            literal (str): The kanji character

        Returns:
            The JLPT kanji entry as a DTO, or `None` when it is not listed
        """
        row = self.session.scalars(
            select(JlptKanji).where(JlptKanji.kanji == literal).limit(1)
        ).first()
        return dtos.JLPTKanjiDTO.model_validate(row) if row else None

    def list_vocab(self, level: int) -> list[dtos.JLPTVocabDTO]:
        """
        Return the full vocabulary study list for a level

        Selects every [`JlptVocab`][kotobase.db.models.JlptVocab] row whose
        `level` equals `level`, ordered by ascending id (insertion order), and
        validates each into a [`JLPTVocabDTO`][kotobase.db.dtos.JLPTVocabDTO]

        Args:
            level (int): The JLPT level from 1 to 5

        Returns:
            Every vocabulary item at the level as DTOs, or `[]` when the level
                is empty
        """
        rows = self.session.scalars(
            select(JlptVocab)
            .where(JlptVocab.level == level)
            .order_by(JlptVocab.id)
        ).all()
        return [dtos.JLPTVocabDTO.model_validate(row) for row in rows]

    def list_kanji(self, level: int) -> list[dtos.JLPTKanjiDTO]:
        """
        Return the full kanji study list for a level

        Selects every [`JlptKanji`][kotobase.db.models.JlptKanji] row whose
        `level` equals `level`, ordered by ascending id (insertion order), and
        validates each into a [`JLPTKanjiDTO`][kotobase.db.dtos.JLPTKanjiDTO]

        Args:
            level (int): The JLPT level from 1 to 5

        Returns:
            Every kanji item at the level as DTOs, or `[]` when the level is
                empty
        """
        rows = self.session.scalars(
            select(JlptKanji)
            .where(JlptKanji.level == level)
            .order_by(JlptKanji.id)
        ).all()
        return [dtos.JLPTKanjiDTO.model_validate(row) for row in rows]

    def list_grammar(self, level: int) -> list[dtos.JLPTGrammarDTO]:
        """
        Return the full grammar study list for a level

        Selects every [`JlptGrammar`][kotobase.db.models.JlptGrammar] row whose
        `level` equals `level`, ordered by ascending id (insertion order), then
        validates each row into a
        [`JLPTGrammarDTO`][kotobase.db.dtos.JLPTGrammarDTO]

        Args:
            level (int): The JLPT level from 1 to 5

        Returns:
            Every grammar point at the level as DTOs, or `[]` when the level is
                empty
        """
        rows = self.session.scalars(
            select(JlptGrammar)
            .where(JlptGrammar.level == level)
            .order_by(JlptGrammar.id)
        ).all()
        return [dtos.JLPTGrammarDTO.model_validate(row) for row in rows]


# --- Tags and audio ---
class TagRepo(KotobaseRepo):
    """
    Repository for the tag dictionary that expands codes to descriptions
    """

    def labels(self, codes: Sequence[str]) -> dict[str, str]:
        """
        Map tag codes to their human readable descriptions

        De-duplicates `codes`, then selects `(code, description)` from
        [`Tag`][kotobase.db.models.Tag] where `code` is `IN` that set. Because
        the lookup is by `code` alone (not by category), a code shared across
        tag families collapses to a single description. An empty input returns
        `{}` without a query

        Args:
            codes (Sequence[str]): The tag codes to expand

        Returns:
            A mapping of code to description for the codes that are known,
                omitting any that are not in the tag table
        """
        wanted = list(dict.fromkeys(codes))
        if not wanted:
            return {}
        rows = self.session.execute(
            select(Tag.code, Tag.description).where(Tag.code.in_(wanted))
        )
        return {row.code: row.description for row in rows}


class AudioRepo(KotobaseRepo):
    """
    Repository for pronunciation audio metadata and clip bytes

    The `audio` table lives in the optional audio pack, attached to the
    connection only when installed. When it is absent the underlying query
    raises an `OperationalError`, which both methods translate into an
    [`AudioDatabaseNotFoundError`][kotobase.exceptions.AudioDatabaseNotFoundError]
    after rolling back the session
    """

    def for_key(
        self,
        key: str,
        *,
        kind: str | None = None,
    ) -> list[dtos.AudioDTO]:
        """
        Fetch audio clip metadata for a lookup key

        Selects [`Audio`][kotobase.db.models.Audio] rows whose `key` equals
        `key` exactly, optionally narrowed to a single `kind`, and validates
        each into an [`AudioDTO`][kotobase.db.dtos.AudioDTO], which carries
        provenance and format metadata but not the raw `data` bytes. When the
        audio pack is not attached the query raises `OperationalError`, which
        is caught, the session is rolled back, and an
        `AudioDatabaseNotFoundError` is raised instead

        Args:
            key (str): The lookup key, such as a kanji or word
            kind (str | None): Restrict to a clip kind when given

        Returns:
            The matching audio clips as metadata DTOs without the raw bytes, or
                `[]` when none match

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
            raise AudioDatabaseNotFoundError(
                "Couldn't Find The Audio Database. Run "
                "`kotobase db pull --with-audio` Or "
                "`kotobase db build --with-audio` To Get It"
            ) from None
        return [dtos.AudioDTO.model_validate(row) for row in rows]

    def payloads(
        self,
        key: str,
        *,
        reading: str | None = None,
        kind: str | None = None,
    ) -> list[tuple[str, bytes]]:
        """
        Fetch the file name and raw bytes of each matching audio clip

        Selects [`Audio`][kotobase.db.models.Audio] rows whose `key` equals
        `key` exactly, optionally narrowed by exact `reading` and/or `kind`.
        Rows whose `data` is `None` (metadata-only entries, such as remote
        clips) are skipped. For the rest, a download file name is built as
        `<reading or key>.<fmt or "mp3">` and paired with the raw bytes. When
        the audio pack is not attached the query raises `OperationalError`,
        which is caught, the session is rolled back, and an
        `AudioDatabaseNotFoundError` is raised instead

        Args:
            key (str): The lookup key, such as a kanji or word
            reading (str | None): Restrict to a single clip reading when given
            kind (str | None): Restrict to a clip kind when given

        Returns:
            A `(file name, bytes)` pair for every matching clip that has
                bundled audio, or `[]` when none match or none carry bytes

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
            raise AudioDatabaseNotFoundError(
                "Couldn't Find The Audio Database. Run "
                "`kotobase db pull --with-audio` Or "
                "`kotobase db build --with-audio` To Get It"
            ) from None
        result: list[tuple[str, bytes]] = []
        for row in rows:
            if row.data is None:
                continue
            name = f"{row.reading or key}.{row.fmt or 'mp3'}"
            result.append((name, row.data))
        return result
