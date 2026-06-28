"""
Defines Kotobase's Data-Transfer-Objects

The DTO's are the boundary between the database and the public API.
[`Repositories`][kotobase.db.repos] return them rather than
[`ORM`][kotobase.db.models] rows so that callers get plain, immutable,
serializable objects that don't depend on an open session

info: Serialization
    Every object inherits from [`Serializable`][kotobase.db.dtos.Serializable],
    which adds `to_dict`, `to_json` and iteration to every DTO

info: ORM Mapping
    - Each object exposes a `from_orm` classmethod that builds it from a
      loaded ORM row

    - Nested objects delegate to each other, so `JMDictEntryDTO.from_orm`
      builds its senses through `SenseDTO.from_orm` and so on

    - The classmethods expect the relationships they read to be eagerly-loaded
      , which is done by the [`Repositories`][kotobase.db.repos]
"""

from __future__ import annotations

import json
from collections.abc import Iterator, Sequence
from dataclasses import asdict, dataclass
from dataclasses import field as dfield
from typing import Any

from . import models as orm


class Serializable:
    """
    Mixin that adds `dict` + `JSON` serialization to a python dataclass
    """

    def to_dict(self) -> dict[str, Any]:
        """
        Converts the object to a plain dictionary

        Returns:
            A nested dictionary of the `dataclass` fields
        """
        return asdict(self)  # type: ignore[call-overload,no-any-return]

    def to_json(self, **json_kwargs: Any) -> str:
        """
        Converts the object to a `JSON` string

        Args:
            **json_kwargs (Any): Extra keyword arguments forwarded to
                `json.dumps`

        Returns:
            The object encoded as compact `JSON` with non-ASCII characters
                kept verbatim
        """
        json_kwargs.setdefault("ensure_ascii", False)
        json_kwargs.setdefault("separators", (",", ":"))
        return json.dumps(self.to_dict(), **json_kwargs)

    def __iter__(self) -> Iterator[tuple[str, Any]]:
        """
        Iterates over the object's fields as key and value pairs

        Yields:
            Each field name paired with its value
        """
        yield from self.to_dict().items()


# --- JMdict ---
@dataclass(slots=True)
class GlossDTO(Serializable):
    """
    A single translation of a `JMdict` sense

    Attributes:
        text (str): The translated text
        lang (str): ISO 639 language code of the gloss
        gender (str | None): Grammatical gender when given
        gtype (str | None): Gloss type such as `lit`, `fig`, `expl` or `tm`
    """

    text: str
    lang: str = "eng"
    gender: str | None = None
    gtype: str | None = None

    @classmethod
    def from_orm(cls, gloss: orm.JMDictGloss) -> GlossDTO:
        """
        Build a gloss from an ORM gloss row

        Args:
            gloss (orm.JMDictGloss): The ORM gloss row

        Returns:
            The gloss as a data transfer object
        """
        return cls(
            text=gloss.text,
            lang=gloss.lang,
            gender=gloss.gender,
            gtype=gloss.gtype,
        )


@dataclass(slots=True)
class SenseDTO(Serializable):
    """
    One meaning of a `JMdict` entry with its glosses and tags

    Attributes:
        glosses (list[GlossDTO]): The translations of the sense
        pos (list[str]): Part of speech tag codes
        field (list[str]): Field of application tag codes
        misc (list[str]): Register tag codes such as `sl` for slang
        dialect (list[str]): Dialect tag codes
        info (list[str]): Free text sense notes
        xref (list[str]): Cross references to related entries
        antonym (list[str]): Antonym references
        lsource (list[dict]): Source language records for loanwords
    """

    glosses: list[GlossDTO] = dfield(default_factory=list)
    pos: list[str] = dfield(default_factory=list)
    field: list[str] = dfield(default_factory=list)
    misc: list[str] = dfield(default_factory=list)
    dialect: list[str] = dfield(default_factory=list)
    info: list[str] = dfield(default_factory=list)
    xref: list[str] = dfield(default_factory=list)
    antonym: list[str] = dfield(default_factory=list)
    lsource: list[dict[str, Any]] = dfield(default_factory=list)

    @classmethod
    def from_orm(cls, sense: orm.JMDictSense) -> SenseDTO:
        """
        Build a sense from an ORM sense row

        Args:
            sense (orm.JMDictSense): The ORM sense row with its glosses loaded

        Returns:
            The sense as a data transfer object
        """
        return cls(
            glosses=[GlossDTO.from_orm(gloss) for gloss in sense.glosses],
            pos=sense.pos,
            field=sense.field,
            misc=sense.misc,
            dialect=sense.dialect,
            info=sense.info,
            xref=sense.xref,
            antonym=sense.antonym,
            lsource=sense.lsource,
        )


@dataclass(slots=True)
class KanjiFormDTO(Serializable):
    """
    A written form of a `JMdict` entry

    Attributes:
        text (str): The kanji spelling
        is_common (bool): True when the form carries a common priority marker
        info (list[str]): Spelling information tag codes
        priority (list[str]): Priority code list
    """

    text: str
    is_common: bool = False
    info: list[str] = dfield(default_factory=list)
    priority: list[str] = dfield(default_factory=list)

    @classmethod
    def from_orm(cls, form: orm.JMDictKanji) -> KanjiFormDTO:
        """
        Build a kanji form from an ORM kanji form row

        Args:
            form (orm.JMDictKanji): The ORM kanji form row

        Returns:
            The form as a data transfer object
        """
        return cls(
            text=form.text,
            is_common=form.is_common,
            info=form.info,
            priority=form.priority,
        )


@dataclass(slots=True)
class KanaFormDTO(Serializable):
    """
    A reading form of a `JMdict` entry

    Attributes:
        text (str): The kana reading
        is_common (bool): True when the reading carries a common priority
            marker
        no_kanji (bool): True when the reading applies to no kanji form
        restrictions (list[str]): Kanji forms the reading is limited to
        info (list[str]): Reading information tag codes
        priority (list[str]): Priority code list
    """

    text: str
    is_common: bool = False
    no_kanji: bool = False
    restrictions: list[str] = dfield(default_factory=list)
    info: list[str] = dfield(default_factory=list)
    priority: list[str] = dfield(default_factory=list)

    @classmethod
    def from_orm(cls, form: orm.JMDictKana) -> KanaFormDTO:
        """
        Build a kana form from an ORM kana form row

        Args:
            form (orm.JMDictKana): The ORM kana form row

        Returns:
            The form as a data transfer object
        """
        return cls(
            text=form.text,
            is_common=form.is_common,
            no_kanji=form.no_kanji,
            restrictions=form.restrictions,
            info=form.info,
            priority=form.priority,
        )


@dataclass(slots=True)
class JMDictEntryDTO(Serializable):
    """
    One `JMdict` dictionary entry

    Attributes:
        id (int): The JMdict sequence number
        is_common (bool): True when the entry is marked common
        freq_rank (int | None): Frequency band where a lower value is more
            frequent
        kanji (list[KanjiFormDTO]): Written forms of the entry
        kana (list[KanaFormDTO]): Reading forms of the entry
        senses (list[SenseDTO]): Meanings of the entry
    """

    id: int
    is_common: bool = False
    freq_rank: int | None = None
    kanji: list[KanjiFormDTO] = dfield(default_factory=list)
    kana: list[KanaFormDTO] = dfield(default_factory=list)
    senses: list[SenseDTO] = dfield(default_factory=list)

    @classmethod
    def from_orm(cls, entry: orm.JMDictEntry) -> JMDictEntryDTO:
        """
        Build an entry from an ORM entry row

        Args:
            entry (orm.JMDictEntry): The ORM entry with its forms and senses
                eagerly-loaded

        Returns:
            The entry as a data transfer object
        """
        return cls(
            id=entry.id,
            is_common=entry.is_common,
            freq_rank=entry.freq_rank,
            kanji=[KanjiFormDTO.from_orm(form) for form in entry.kanji],
            kana=[KanaFormDTO.from_orm(form) for form in entry.kana],
            senses=[SenseDTO.from_orm(sense) for sense in entry.senses],
        )

    @property
    def headword(self) -> str:
        """
        Returns the primary written form of the entry

        Returns:
            The first kanji form when present, otherwise the first reading
        """
        if self.kanji:
            return self.kanji[0].text
        return self.kana[0].text if self.kana else ""


# --- JMnedict ---
@dataclass(slots=True)
class NameTranslationDTO(Serializable):
    """
    A translation block of a `JMnedict` name

    Attributes:
        name_type (list[str]): Name type tag codes such as `place` or `surname`
        translations (list[str]): The translated names
        xref (list[str]): Cross references to related entries
    """

    name_type: list[str] = dfield(default_factory=list)
    translations: list[str] = dfield(default_factory=list)
    xref: list[str] = dfield(default_factory=list)

    @classmethod
    def from_orm(cls, block: orm.JMnedictTranslation) -> NameTranslationDTO:
        """
        Build a translation block from an ORM translation row

        Args:
            block (orm.JMnedictTranslation): The ORM translation block with its
                glosses loaded

        Returns:
            The translation block as a data transfer object
        """
        return cls(
            name_type=block.name_type,
            translations=[gloss.text for gloss in block.glosses],
            xref=block.xref,
        )


@dataclass(slots=True)
class JMNeDictEntryDTO(Serializable):
    """
    One `JMnedict` proper name entry

    Attributes:
        id (int): The JMnedict sequence number
        kanji (list[str]): Written forms of the name
        kana (list[str]): Reading forms of the name
        translations (list[NameTranslationDTO]): Translation blocks
    """

    id: int
    kanji: list[str] = dfield(default_factory=list)
    kana: list[str] = dfield(default_factory=list)
    translations: list[NameTranslationDTO] = dfield(default_factory=list)

    @classmethod
    def from_orm(cls, entry: orm.JMnedictEntry) -> JMNeDictEntryDTO:
        """
        Build a name entry from an ORM entry row

        Args:
            entry (orm.JMnedictEntry): The ORM entry with its forms and
                translations eagerly-loaded

        Returns:
            The entry as a data transfer object
        """
        return cls(
            id=entry.id,
            kanji=[form.text for form in entry.kanji],
            kana=[form.text for form in entry.kana],
            translations=[
                NameTranslationDTO.from_orm(block)
                for block in entry.translations
            ],
        )

    @property
    def headword(self) -> str:
        """
        Returns the primary written form of the name

        Returns:
            The first kanji form when present, otherwise the first reading
        """
        if self.kanji:
            return self.kanji[0]
        return self.kana[0] if self.kana else ""


# --- Kanji ---
@dataclass(slots=True)
class KanjiDTO(Serializable):
    """
    A kanji with its full `KanjiDic2` and `KanjiVG` profile

    Attributes:
        literal (str): The kanji character
        grade (int | None): School grade in which it is taught
        stroke_count (int | None): Accepted stroke count
        freq (int | None): Newspaper frequency rank
        jlpt_old (int | None): Pre 2010 JLPT class from KanjiDic2
        jlpt_tanos (int | None): JLPT level from the Tanos lists
        onyomi (list[str]): On readings
        kunyomi (list[str]): Kun readings
        nanori (list[str]): Name only readings
        pinyin (list[str]): Mandarin pinyin readings
        korean (list[str]): Korean readings
        meanings (list[str]): English meanings
        radicals (list[str]): Radical components of the kanji
        dic_refs (dict[str, str]): Dictionary references keyed by type, such as
            `nelson_c` or `heisig`
        query_codes (dict[str, list[str]]): Lookup codes keyed by type, such as
            `skip` and `four_corner`
        codepoints (dict[str, str]): Encoding codepoints keyed by type
        variants (list[dict[str, Any]]): Variant form references with their
            type and value
        has_stroke_order (bool): True when KanjiVG stroke data is available
    """

    literal: str
    grade: int | None = None
    stroke_count: int | None = None
    freq: int | None = None
    jlpt_old: int | None = None
    jlpt_tanos: int | None = None
    onyomi: list[str] = dfield(default_factory=list)
    kunyomi: list[str] = dfield(default_factory=list)
    nanori: list[str] = dfield(default_factory=list)
    pinyin: list[str] = dfield(default_factory=list)
    korean: list[str] = dfield(default_factory=list)
    meanings: list[str] = dfield(default_factory=list)
    radicals: list[str] = dfield(default_factory=list)
    dic_refs: dict[str, str] = dfield(default_factory=dict)
    query_codes: dict[str, list[str]] = dfield(default_factory=dict)
    codepoints: dict[str, str] = dfield(default_factory=dict)
    variants: list[dict[str, Any]] = dfield(default_factory=list)
    has_stroke_order: bool = False

    @classmethod
    def from_orm(
        cls,
        kanji: orm.Kanji,
        *,
        radicals: Sequence[str] = (),
        jlpt_tanos: int | None = None,
    ) -> KanjiDTO:
        """
        Build a kanji profile from an ORM kanji row

        Args:
            kanji (orm.Kanji): The ORM kanji with its readings, meanings,
                nanori, dic refs, query codes, variants, codepoints and stroke
                data eagerly-loaded
            radicals (Sequence[str]): Radical components for the kanji, which
                are not a direct relationship and so are passed in
            jlpt_tanos (int | None): The Tanos JLPT level when known

        Returns:
            The kanji as a data transfer object
        """
        query_codes: dict[str, list[str]] = {}
        for code in kanji.query_codes:
            query_codes.setdefault(code.type, []).append(code.value)
        korean = ("korean_r", "korean_h")
        return cls(
            literal=kanji.literal,
            grade=kanji.grade,
            stroke_count=kanji.stroke_count,
            freq=kanji.freq,
            jlpt_old=kanji.jlpt_old,
            jlpt_tanos=jlpt_tanos,
            onyomi=[r.value for r in kanji.readings if r.type == "ja_on"],
            kunyomi=[r.value for r in kanji.readings if r.type == "ja_kun"],
            nanori=[n.value for n in kanji.nanori],
            pinyin=[r.value for r in kanji.readings if r.type == "pinyin"],
            korean=[r.value for r in kanji.readings if r.type in korean],
            meanings=[m.value for m in kanji.meanings if m.lang == "en"],
            radicals=list(radicals),
            dic_refs={ref.type: ref.value for ref in kanji.dic_refs},
            query_codes=query_codes,
            codepoints={cp.type: cp.value for cp in kanji.codepoints},
            variants=[
                {"type": v.type, "value": v.value} for v in kanji.variants
            ],
            has_stroke_order=kanji.strokes is not None,
        )


# --- Furigana, Sentences, JLPT ---
@dataclass(slots=True)
class FuriganaDTO(Serializable):
    """
    Furigana segmentation for a spelling and reading pair

    Attributes:
        text (str): The written spelling
        reading (str): The full kana reading
        segments (list[dict]): Alignment of spelling spans to their readings
    """

    text: str
    reading: str
    segments: list[dict[str, Any]] = dfield(default_factory=list)

    @classmethod
    def from_orm(cls, row: orm.Furigana) -> FuriganaDTO:
        """
        Build a furigana object from an ORM furigana row

        Args:
            row (orm.Furigana): The ORM furigana row

        Returns:
            The row as a data transfer object
        """
        return cls(
            text=row.text,
            reading=row.reading,
            segments=row.segments,
        )


@dataclass(slots=True)
class SentenceDTO(Serializable):
    """
    A `Tatoeba` example sentence with its translations

    Attributes:
        id (int): The Tatoeba sentence identifier
        text (str): The sentence text
        lang (str): ISO 639 language code of the sentence
        translations (list[str]): Aligned translations in other languages
    """

    id: int
    text: str
    lang: str = "jpn"
    translations: list[str] = dfield(default_factory=list)

    @classmethod
    def from_orm(
        cls,
        row: orm.Sentence,
        *,
        translations: Sequence[str] = (),
    ) -> SentenceDTO:
        """
        Build a sentence from an ORM sentence row

        Args:
            row (orm.Sentence): The ORM sentence row
            translations (Sequence[str]): Aligned translation texts when known

        Returns:
            The row as a data transfer object
        """
        return cls(
            id=row.id,
            text=row.text,
            lang=row.lang,
            translations=list(translations),
        )


@dataclass(slots=True)
class JLPTVocabDTO(Serializable):
    """
    A Tanos JLPT vocabulary item

    Attributes:
        level (int): JLPT level from 1 to 5
        word (str | None): The headword
        reading (str | None): The kana reading
        meaning (str | None): The English meaning
    """

    level: int
    word: str | None = None
    reading: str | None = None
    meaning: str | None = None

    @classmethod
    def from_orm(cls, row: orm.JlptVocab) -> JLPTVocabDTO:
        """
        Build a JLPT vocabulary item from an ORM row

        Args:
            row (orm.JlptVocab): The ORM JLPT vocabulary row

        Returns:
            The row as a data transfer object
        """
        return cls(
            level=row.level,
            word=row.word,
            reading=row.reading,
            meaning=row.meaning,
        )


@dataclass(slots=True)
class JLPTKanjiDTO(Serializable):
    """
    A Tanos JLPT kanji item

    Attributes:
        level (int): JLPT level from 1 to 5
        kanji (str): The kanji character
        on_yomi (str | None): On readings
        kun_yomi (str | None): Kun readings
        meaning (str | None): The English meaning
    """

    level: int
    kanji: str
    on_yomi: str | None = None
    kun_yomi: str | None = None
    meaning: str | None = None

    @classmethod
    def from_orm(cls, row: orm.JlptKanji) -> JLPTKanjiDTO:
        """
        Build a JLPT kanji item from an ORM row

        Args:
            row (orm.JlptKanji): The ORM JLPT kanji row

        Returns:
            The row as a data transfer object
        """
        return cls(
            level=row.level,
            kanji=row.kanji,
            on_yomi=row.on_yomi,
            kun_yomi=row.kun_yomi,
            meaning=row.meaning,
        )


@dataclass(slots=True)
class JLPTGrammarDTO(Serializable):
    """
    A Tanos JLPT grammar point

    Attributes:
        level (int): JLPT level from 1 to 5
        grammar (str): The grammar point
        formation (str | None): How the grammar point is formed
        examples (list[str]): Example sentences
    """

    level: int
    grammar: str
    formation: str | None = None
    examples: list[str] = dfield(default_factory=list)

    @classmethod
    def from_orm(cls, row: orm.JlptGrammar) -> JLPTGrammarDTO:
        """
        Build a JLPT grammar point from an ORM row

        Args:
            row (orm.JlptGrammar): The ORM JLPT grammar row

        Returns:
            The row as a data transfer object
        """
        return cls(
            level=row.level,
            grammar=row.grammar,
            formation=row.formation,
            examples=row.examples,
        )


# --- Radicals, Audio ---
@dataclass(slots=True)
class RadicalDTO(Serializable):
    """
    A search radical and its stroke count

    Attributes:
        radical (str): The radical character
        stroke_count (int | None): Number of strokes in the radical
    """

    radical: str
    stroke_count: int | None = None

    @classmethod
    def from_orm(cls, row: orm.Radical) -> RadicalDTO:
        """
        Build a radical from an ORM radical row

        Args:
            row (orm.Radical): The ORM radical row

        Returns:
            The row as a data transfer object
        """
        return cls(radical=row.radical, stroke_count=row.stroke_count)


@dataclass(slots=True)
class AudioDTO(Serializable):
    """
    Metadata for a pronunciation audio clip

    Attributes:
        kind (str): What the clip pronounces, such as `kanji_word`
        key (str): Lookup key for the clip
        reading (str | None): The reading the clip pronounces when relevant
        fmt (str | None): Audio container or codec such as `mp3`
        source (str): Name of the upstream source
        license (str | None): License identifier for the clip
        attribution (str | None): Required attribution text or link
    """

    kind: str
    key: str
    reading: str | None = None
    fmt: str | None = None
    source: str = ""
    license: str | None = None
    attribution: str | None = None

    @classmethod
    def from_orm(cls, row: orm.Audio) -> AudioDTO:
        """
        Build audio metadata from an ORM audio row

        Args:
            row (orm.Audio): The ORM audio row

        Returns:
            The row as a data transfer object, without the raw bytes
        """
        return cls(
            kind=row.kind,
            key=row.key,
            reading=row.reading,
            fmt=row.fmt,
            source=row.source,
            license=row.license,
            attribution=row.attribution,
        )


# --- Aggregate Lookup Result ---
@dataclass(slots=True)
class LookupResult(Serializable):
    """
    The aggregated result of a comprehensive word lookup

    Attributes:
        query (str): The query that produced the result
        entries (list[JMDictEntryDTO]): Matching dictionary entries
        names (list[JMNeDictEntryDTO]): Matching proper names
        kanji (list[KanjiDTO]): Details for each kanji in the query
        furigana (list[FuriganaDTO]): Furigana for the matched forms
        jlpt_vocab (JLPTVocabDTO | None): JLPT vocabulary entry for the word
        jlpt_kanji_levels (dict[str, int]): JLPT level per kanji in the query
        jlpt_grammar (list[JLPTGrammarDTO]): JLPT grammar points matching the
            query
        sentences (list[SentenceDTO]): Example sentences containing the query
        labels (dict[str, str]): Tag code to human description map, populated
            only when labels are requested
    """

    query: str
    entries: list[JMDictEntryDTO] = dfield(default_factory=list)
    names: list[JMNeDictEntryDTO] = dfield(default_factory=list)
    kanji: list[KanjiDTO] = dfield(default_factory=list)
    furigana: list[FuriganaDTO] = dfield(default_factory=list)
    jlpt_vocab: JLPTVocabDTO | None = None
    jlpt_kanji_levels: dict[str, int] = dfield(default_factory=dict)
    jlpt_grammar: list[JLPTGrammarDTO] = dfield(default_factory=list)
    sentences: list[SentenceDTO] = dfield(default_factory=list)
    labels: dict[str, str] = dfield(default_factory=dict)

    def has_jlpt(self) -> bool:
        """
        Report whether the result carries any JLPT information

        Returns:
            True when a JLPT vocabulary entry or kanji level is present
        """
        return self.jlpt_vocab is not None or bool(self.jlpt_kanji_levels)
