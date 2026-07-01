"""
Kotobase's Public API

[`Kotobase`][kotobase.api.Kotobase] is a thin, stateless wrapper over the
[`Unit Of Work`][kotobase.db.uow] which queries the databases

Each call opens one read-only session, runs the queries it needs through
the [`repositories`][kotobase.db.repos] and returns plain
[`Data Transfer Objects`][kotobase.db.dtos]

The queries in a `lookup` run sequentially on a single session, which is both
simple and correct for read-only `SQLite`
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from sqlalchemy import text

from .db.dtos import (
    AudioDTO,
    FuriganaDTO,
    JLPTGrammarDTO,
    JLPTKanjiDTO,
    JLPTVocabDTO,
    JMDictEntryDTO,
    JMNeDictEntryDTO,
    KanaFormDTO,
    KanjiDTO,
    KanjiFormDTO,
    Keyed,
    LookupResult,
    RadicalDTO,
    SenseDTO,
    SentenceDTO,
)
from .db.uow import UnitOfWork
from .exceptions import APIError

_JLPT_LIST_METHODS = {
    "vocab": "list_vocab",
    "kanji": "list_kanji",
    "grammar": "list_grammar",
}


def _kanji_in(word: str) -> list[str]:
    """
    Extract the unique `kanji` characters from a string in order

    Args:
        word (str): The text to scan

    Returns:
        The distinct kanji characters in the order they appear
    """
    found = [c for c in word if "一" <= c <= "鿿"]
    return list(dict.fromkeys(found))


def _collect_codes(
    entries: list[JMDictEntryDTO],
    names: list[JMNeDictEntryDTO],
) -> list[str]:
    """
    Gather every `JMDict` / `JMNedict` tag code present in a set of entries
    and names

    Args:
        entries (list[JMDictEntryDTO]): The dictionary entries to scan
        names (list[JMNeDictEntryDTO]): The proper names to scan

    Returns:
        The set of tag codes used across the entries and names
    """
    codes: set[str] = set()
    for entry in entries:
        for sense in entry.senses:
            codes.update(sense.pos, sense.field, sense.misc, sense.dialect)
        for kanji_form in entry.kanji:
            codes.update(kanji_form.info)
        for kana_form in entry.kana:
            codes.update(kana_form.info)
    for name in names:
        for block in name.translations:
            codes.update(block.name_type)
    return list(codes)


def _key(value: str | Keyed) -> str:
    """
    Coerce a lookup key, or a DTO that carries one, to its key string

    A plain string passes through unchanged. Any DTO satisfying
    [`Keyed`][kotobase.db.dtos.Keyed] returns its own `key`, so a result from
    one call can be passed straight into another method without unpacking a
    field by hand

    Args:
        value (str | Keyed): A key string, or a DTO that carries a lookup key

    Returns:
        The lookup key as a string
    """
    return value if isinstance(value, str) else value.key


class Kotobase:
    """
    Stateless entry point for querying the kotobase database
    """

    def lookup(
        self,
        query: str,
        *,
        wildcard: bool = False,
        include_names: bool = False,
        sentence_limit: int | None = 50,
        entry_limit: int | None = None,
        with_labels: bool = False,
    ) -> LookupResult:
        """
        Run a comprehensive lookup across every data source

        Args:
            query (str): The query, written in kana or kanji, where `*` and `%`
                act as wildcards when `wildcard` is True
            wildcard (bool): When True, match forms as a `LIKE` pattern
            include_names (bool): When True, also search JMnedict proper names
            sentence_limit (int | None): Maximum number of example
                sentences to return
            entry_limit (int | None): Maximum number of dictionary entries to
                return, or None for no limit
            with_labels (bool): When True, resolve every tag code in the result
                to its human-readable description and store them on the result

        Returns:
            A [`LookupResult`][kotobase.db.dtos.LookupResult] aggregating
                entries, names, kanji, furigana, JLPT data and example
                sentences
        """
        query = query.strip()
        # Get All Unique Kanji Present In `word`
        kanji_chars = _kanji_in(query)
        with UnitOfWork() as uow:
            # JMDict
            entries = uow.jmdict.search_form(
                query,
                wildcard=wildcard,
                limit=entry_limit,
            )

            # JMNedict
            names = (
                uow.jmnedict.search(
                    query,
                    wildcard=wildcard,
                    limit=entry_limit,
                )
                if include_names
                else []
            )

            # Fetch All Unique Kanji
            kanji = uow.kanji.bulk_fetch(kanji_chars)

            # JmdictFurigana
            furigana = uow.furigana.for_text(query)

            # TANOS
            jlpt_vocab = uow.jlpt.vocab_by_word(query)
            jlpt_levels = uow.jlpt.kanji_levels(kanji_chars)
            jlpt_grammar = uow.jlpt.grammar_like(query)

            # Tatoeba
            sentences = uow.sentences.search_containing(
                query,
                limit=sentence_limit,
                wildcard=wildcard,
            )

            # Tag Code Descriptions
            labels = (
                uow.tags.labels(_collect_codes(entries, names))
                if with_labels
                else {}
            )

        return LookupResult(
            query=query,
            entries=entries,
            names=names,
            kanji=kanji,
            furigana=furigana,
            jlpt_vocab=jlpt_vocab,
            jlpt_kanji_levels=jlpt_levels,
            jlpt_grammar=jlpt_grammar,
            sentences=sentences,
            labels=labels,
        )

    def kanji(
        self,
        literal: str | KanjiDTO | KanjiFormDTO,
    ) -> KanjiDTO | None:
        """
        Return the full profile of a single kanji

        Args:
            literal (str | KanjiDTO | KanjiFormDTO): The kanji, as a character
                or a DTO to read it from

        Returns:
            The kanji details, or None when it is not in the database
        """
        with UnitOfWork() as uow:
            return uow.kanji.by_literal(_key(literal))

    def search_kanji(
        self,
        *,
        stroke_count: int | None = None,
        grade: int | None = None,
        freq_max: int | None = None,
        jlpt: int | None = None,
        limit: int | None = 100,
    ) -> list[KanjiDTO]:
        """
        Search kanji by its scalar attributes

        Args:
            stroke_count (int | None): Required stroke count
            grade (int | None): Required school grade
            freq_max (int | None): Maximum newspaper frequency rank
            jlpt (int | None): Required Tanos JLPT level
            limit (int | None): Maximum number of kanji to return

        Returns:
            The matching kanji ordered by frequency then character
        """
        with UnitOfWork() as uow:
            return uow.kanji.search(
                stroke_count=stroke_count,
                grade=grade,
                freq_max=freq_max,
                jlpt=jlpt,
                limit=limit,
            )

    def kanji_by_skip(
        self,
        code: str,
        *,
        limit: int | None = 100,
    ) -> list[KanjiDTO]:
        """
        Find kanji with a given `SKIP` query code

        Args:
            code (str): The SKIP code such as `1-4-3`
            limit (int | None): Maximum number of kanji to return

        Returns:
            The matching kanji as data transfer objects
        """
        with UnitOfWork() as uow:
            return uow.kanji.by_skip(code, limit=limit)

    def stroke_svg(
        self,
        literal: str | KanjiDTO,
        *,
        raw: bool = False,
    ) -> str | None:
        """
        Return a kanji's stroke order as SVG

        By default this returns a self-contained, browser renderable SVG
        document. Pass `raw` to get the original KanjiVG `<kanji>` fragment
        instead, which has no `<svg>` root or styling

        Args:
            literal (str | KanjiDTO): The kanji string or a `KanjiDTO` object
            raw (bool): When True, return the raw KanjiVG fragment unwrapped

        Returns:
            The stroke order SVG, or None when not available
        """
        with UnitOfWork() as uow:
            return uow.kanji.stroke_svg(_key(literal), raw=raw)

    def radicals(self) -> list[RadicalDTO]:
        """
        Return every search radical with its stroke count

        Returns:
            The radicals ordered by stroke count
        """
        with UnitOfWork() as uow:
            return uow.radicals.list_radicals()

    def by_radicals(
        self,
        radicals: Sequence[str | RadicalDTO],
        *,
        match: str = "all",
    ) -> list[KanjiDTO]:
        """
        Return the kanji that contain the given radicals

        Args:
            radicals (list[str | RadicalDTO]): The radical components to match,
                given as characters or RadicalDTO objects
            match (str): `all` to require every radical (intersection), or
                `any` to match kanji that contain at least one (union)

        Returns:
            The full details of each matching kanji

        Raises:
            APIError: If `match` is not `all` or `any`
        """
        if match not in ("all", "any"):
            raise APIError("Match Must Be 'all' Or 'any'")
        chars = [_key(radical) for radical in radicals]
        with UnitOfWork() as uow:
            literals = uow.radicals.kanji_by_radicals(chars, match=match)
            return uow.kanji.bulk_fetch(literals)

    def jlpt_level(
        self,
        word: str | JMDictEntryDTO | JLPTVocabDTO,
    ) -> int | None:
        """
        Return the `JLPT` vocabulary level of a word

        Args:
            word (str | JMDictEntryDTO | JLPTVocabDTO): The word, as text or a
                DTO to read it from

        Returns:
            The JLPT level from 1 to 5, or None when the word is not listed
        """
        with UnitOfWork() as uow:
            vocab = uow.jlpt.vocab_by_word(_key(word))
        return vocab.level if vocab else None

    def jlpt_list(
        self,
        kind: str,
        level: int,
    ) -> list[JLPTVocabDTO] | list[JLPTKanjiDTO] | list[JLPTGrammarDTO]:
        """
        Return a full Tanos JLPT study list

        Args:
            kind (str): One of `vocab`, `kanji` or `grammar`
            level (int): The JLPT level from 1 to 5

        Returns:
            Every item of the requested kind at the level

        Raises:
            APIError: If `kind` is not a known JLPT list kind or `level` is
                not between 1 and 5
        """
        if kind not in _JLPT_LIST_METHODS:
            raise APIError(f"Unknown JLPT Kind : {kind!r}")
        if level not in range(1, 6):
            raise APIError(f"JLPT Level Must Be 1 To 5, Got {level!r}")
        with UnitOfWork() as uow:
            if kind == "vocab":
                return uow.jlpt.list_vocab(level)
            if kind == "kanji":
                return uow.jlpt.list_kanji(level)
            return uow.jlpt.list_grammar(level)

    def names(
        self,
        form: str | JMNeDictEntryDTO | None = None,
        *,
        name_type: str | None = None,
        wildcard: bool = False,
        limit: int | None = 50,
    ) -> list[JMNeDictEntryDTO]:
        """
        Look up or browse `JMnedict` proper names

        Args:
            form (str | JMNeDictEntryDTO | None): A written or reading form to
                search for, as text or a name DTO to read it from
            name_type (str | None): A name type to browse, such as `place`
            wildcard (bool): When True, match the form as a `LIKE` pattern
            limit (int | None): Maximum number of names to return

        Returns:
            The matching names, empty when neither a form nor a type is given
        """
        with UnitOfWork() as uow:
            if name_type is not None:
                return uow.jmnedict.browse_by_type(name_type, limit=limit)
            if form is not None:
                return uow.jmnedict.search(
                    _key(form),
                    wildcard=wildcard,
                    limit=limit,
                )
            return []

    def sentences(
        self,
        text_value: str | JMDictEntryDTO,
        *,
        limit: int | None = 20,
    ) -> list[SentenceDTO]:
        """
        Return `Tatoeba` Japanese example sentences containing the given text

        Args:
            text_value (str | JMDictEntryDTO): The text to search for, as a
                string or a dictionary entry to read its headword from
            limit (int | None): Maximum number of sentences to return

        Returns:
            The matching example sentences
        """
        with UnitOfWork() as uow:
            return uow.sentences.search_containing(
                _key(text_value), limit=limit
            )

    def words_with_kanji(
        self,
        kanji: str | KanjiDTO,
        *,
        limit: int | None = 50,
    ) -> list[JMDictEntryDTO]:
        """
        Return dictionary entries whose written form uses a kanji

        Args:
            kanji (str | KanjiDTO): The kanji character, or a KanjiDTO to read
                the character from
            limit (int | None): Maximum entries to return, or None for no limit

        Returns:
            The entries that use the kanji in a written form
        """
        literal = _key(kanji)
        with UnitOfWork() as uow:
            return uow.jmdict.search_form(
                f"*{literal}*", wildcard=True, limit=limit
            )

    def sentences_with_kanji(
        self,
        kanji: str | KanjiDTO,
        *,
        limit: int | None = 20,
    ) -> list[SentenceDTO]:
        """
        Return example sentences that contain a kanji

        Args:
            kanji (str | KanjiDTO): The kanji character, or a KanjiDTO to read
                the character from
            limit (int | None): Maximum number of sentences to return

        Returns:
            The matching example sentences with their translations
        """
        literal = _key(kanji)
        with UnitOfWork() as uow:
            return uow.sentences.search_containing(literal, limit=limit)

    def resolve_references(
        self,
        source: JMDictEntryDTO | SenseDTO | str,
    ) -> list[JMDictEntryDTO]:
        """
        Resolve the cross-references and antonyms of a sense or entry

        Args:
            source (JMDictEntryDTO | SenseDTO | str): The entry or sense whose
                xref and antonym codes to resolve, or a single reference code

        Returns:
            The referenced entries, de-duplicated by sequence number
        """
        if isinstance(source, str):
            codes = [source]
        elif isinstance(source, SenseDTO):
            codes = [*source.xref, *source.antonym]
        else:
            codes = [
                code
                for sense in source.senses
                for code in (*sense.xref, *sense.antonym)
            ]
        seen: dict[int, JMDictEntryDTO] = {}
        with UnitOfWork() as uow:
            for code in codes:
                for entry in uow.jmdict.resolve_reference(code):
                    seen.setdefault(entry.id, entry)
        return list(seen.values())

    def furigana(
        self,
        word: str | JMDictEntryDTO | KanjiFormDTO | KanaFormDTO,
        reading: str | None = None,
    ) -> list[FuriganaDTO]:
        """
        Return furigana segmentation for a written form

        Args:
            word (str | JMDictEntryDTO | KanjiFormDTO | KanaFormDTO): The
                written spelling, as text or a DTO to read it from
            reading (str | None): A specific reading to narrow the match

        Returns:
            The matching furigana segmentations
        """
        with UnitOfWork() as uow:
            return uow.furigana.for_text(_key(word), reading)

    def audio(
        self,
        key: str | KanjiDTO | JMDictEntryDTO,
        *,
        kind: str | None = None,
    ) -> list[AudioDTO]:
        """
        Return pronunciation audio metadata for a lookup key

        Args:
            key (str | KanjiDTO | JMDictEntryDTO): The lookup key, such as a
                kanji or word, as a string or a DTO to read it from
            kind (str | None): Restrict to a clip kind when given

        Returns:
            The matching audio clips as metadata, without the raw bytes

        Raises:
            AudioDatabaseNotFoundError: If the optional audio pack is not
                installed
        """
        with UnitOfWork() as uow:
            return uow.audio.for_key(_key(key), kind=kind)

    def audio_bytes(
        self,
        key: str | KanjiDTO | JMDictEntryDTO,
        *,
        reading: str | None = None,
        kind: str | None = None,
    ) -> list[tuple[str, bytes]]:
        """
        Return the file name and raw bytes of each matching audio clip

        Args:
            key (str | KanjiDTO | JMDictEntryDTO): The lookup key, such as a
                kanji or word, as a string or a DTO to read it from
            reading (str | None): Select a specific clip by its reading, or
                None to return every matching clip
            kind (str | None): Restrict to a clip kind when given

        Returns:
            A file name and bytes pair for every matching clip, empty when
                nothing matches

        Raises:
            AudioDatabaseNotFoundError: If the optional audio pack is not
                installed
        """
        with UnitOfWork() as uow:
            payloads = uow.audio.payloads(
                _key(key), reading=reading, kind=kind
            )
        return payloads

    def save_audio(
        self,
        key: str | KanjiDTO | JMDictEntryDTO,
        dest: str | Path,
        *,
        reading: str | None = None,
        kind: str | None = None,
    ) -> list[Path]:
        """
        Save the matching pronunciation audio clips into a directory

        Args:
            key (str | KanjiDTO | JMDictEntryDTO): The lookup key, such as a
                kanji or word, as a string or a DTO to read it from
            dest (str | Path): The directory to write the clips into, created
                when it does not exist
            reading (str | None): Save only the clip with this reading when
                given
            kind (str | None): Restrict to a clip kind when given

        Returns:
            The paths of the written audio files

        Raises:
            AudioDatabaseNotFoundError: If the optional audio pack is not
                installed
        """
        with UnitOfWork() as uow:
            payloads = uow.audio.payloads(
                _key(key), reading=reading, kind=kind
            )
        if not payloads:
            return []
        directory = Path(dest)
        directory.mkdir(parents=True, exist_ok=True)
        written: list[Path] = []
        for name, data in payloads:
            path = directory / name
            path.write_bytes(data)
            written.append(path)
        return written

    def search_meaning(
        self,
        query: str,
        *,
        limit: int | None = 50,
    ) -> list[JMDictEntryDTO]:
        """
        Return entries whose English meaning matches the query

        Args:
            query (str): The full text search expression to run against glosses
            limit (int | None): Maximum number of entries to return

        Returns:
            The matching dictionary entries
        """
        with UnitOfWork() as uow:
            return uow.jmdict.search_gloss(query, limit=limit)

    def expand_tags(self, codes: list[str]) -> dict[str, str]:
        """
        Expand tag codes to their human readable descriptions

        Args:
            codes (list[str]): The tag codes to expand

        Returns:
            A mapping of code to description for those that are known
        """
        with UnitOfWork() as uow:
            return uow.tags.labels(codes)

    def db_info(self) -> dict[str, str]:
        """
        Return the build metadata recorded in the database

        Returns:
            A mapping of metadata key to value, such as the build date, schema
                version and database size

        Raises:
            DatabaseNotFoundError: If the database does not exist
        """
        from .db.connection import session_scope

        with session_scope() as session:
            rows = session.execute(text("SELECT key, value FROM db_meta"))
            return {row.key: row.value for row in rows}

    def __call__(
        self,
        query: str,
        *,
        wildcard: bool = False,
        include_names: bool = False,
        sentence_limit: int | None = 50,
        entry_limit: int | None = None,
        with_labels: bool = False,
    ) -> LookupResult:
        """
        Run a comprehensive lookup, an alias for
        [`lookup`][kotobase.api.Kotobase.lookup]

        Args:
            query (str): The query, written in kana or kanji
            wildcard (bool): When True, match forms as a `LIKE` pattern
            include_names (bool): When True, also search JMnedict proper names
            sentence_limit (int | None): Maximum number of example
                sentences to return
            entry_limit (int | None): Maximum number of dictionary entries to
                return, or None for no limit
            with_labels (bool): When True, resolve tag codes to descriptions

        Returns:
            A [`LookupResult`][kotobase.db.dtos.LookupResult] for the query
        """
        return self.lookup(
            query,
            wildcard=wildcard,
            include_names=include_names,
            sentence_limit=sentence_limit,
            entry_limit=entry_limit,
            with_labels=with_labels,
        )
