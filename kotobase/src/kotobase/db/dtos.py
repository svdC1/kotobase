"""
Defines Kotobase's Data-Transfer-Objects

The DTOs are the boundary between the database and the public API.
[`Repositories`][kotobase.db.repos] return them rather than
[`ORM`][kotobase.db.models] rows so that callers get plain, immutable,
serializable values that don't depend on an open session

info: Serialization
    Every DTO is a `Pydantic` model, serialize it with Pydantic's own
    `model_dump` / `model_dump_json`, which keep Japanese text verbatim

info: ORM Mapping
    - ORM-backed DTOs inherit from
      [`SafeORMModel`][kotobase.db.dtos.SafeORMModel] and are built with
      `model_validate`, reading attributes straight from a loaded ORM row

    - A model validator replaces any relationship that wasn't eagerly loaded
      with `None`, so validation never triggers a lazy load, and overlays
      values passed through the validation `context` for fields that aren't
      plain ORM attributes, such as a kanji's radicals

    - The [`Repositories`][kotobase.db.repos] eagerly load the relationships
      each DTO reads
"""

from __future__ import annotations

from typing import Any, Protocol, TypeAlias

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationInfo,
    field_validator,
    model_validator,
)
from sqlalchemy import inspect
from sqlalchemy.orm import base


class SafeORMModel(BaseModel):
    """
    Pydantic base model for ORM-backed DTOs that tolerates unloaded
    relationships

    Validates directly from `SQLAlchemy` instances (`from_attributes`), but
    first replaces any relationship field that wasn't eagerly loaded with
    `None` instead of triggering a lazy load, and overlays any values supplied
    through the validation `context`
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @model_validator(mode="before")
    @classmethod
    def check_sqlalchemy_state(cls, data: Any, info: ValidationInfo) -> Any:
        """
        Builds a validation-safe mapping from a `SQLAlchemy` instance

        Reads each field from its ORM attribute (honoring a field's validation
        alias), maps unloaded relationships to `None` so that validation never
        triggers a lazy load, then overlays any matching keys from the
        validation `context`. Inputs that aren't SQLAlchemy instances are
        returned unchanged

        Args:
            data (Any): The value being validated (ORM instance or mapping)
            info (ValidationInfo): Validation context carrying injected fields

        Returns:
            A mapping safe for Pydantic validation, or `data` unchanged when
                it isn't a `SQLAlchemy` instance
        """

        # Check If The Object is an SQLAlchemy Instance
        state = inspect(data, raiseerr=False)
        if state is None:
            # Return Input Object Unchanged
            return data

        # Relationships not eagerly loaded, and attributes already in memory
        unloaded_fields = state.unloaded
        loaded_data = base.instance_dict(data)

        # Build A Safe Dictionary For Pydantic
        safe_dict: dict[str, Any] = {}
        for field_name, field in cls.model_fields.items():
            # A field may read from a differently named ORM attribute
            alias = field.validation_alias
            source = alias if isinstance(alias, str) else field_name
            if source in unloaded_fields:
                # Relationship not loaded, avoid triggering a lazy load
                safe_dict[field_name] = None
            elif source in loaded_data:
                safe_dict[field_name] = loaded_data[source]
            else:
                # Calculated fields / hybrids not present in instance_dict
                safe_dict[field_name] = getattr(data, source, None)

        # Overlay repo-injected fields that aren't plain ORM attributes
        if info.context:
            safe_dict.update(
                {
                    key: value
                    for key, value in info.context.items()
                    if key in cls.model_fields
                }
            )
        return safe_dict


class Keyed(Protocol):
    """
    Interface for a DTO that carries its own lookup key

    The public API accepts these DTOs anywhere a string key is expected and
    reads the key straight off the object, so a result from one call can be
    passed into another without unpacking a field by hand
    """

    @property
    def key(self) -> str:
        """
        Return the DTO's natural lookup key

        Returns:
            The key string, such as a kanji literal or an entry's headword
        """
        ...


# --- JMdict ---
class GlossDTO(SafeORMModel):
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


class SenseDTO(SafeORMModel):
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

    glosses: list[GlossDTO] = Field(default_factory=list)
    pos: list[str] = Field(default_factory=list)
    field: list[str] = Field(default_factory=list)
    misc: list[str] = Field(default_factory=list)
    dialect: list[str] = Field(default_factory=list)
    info: list[str] = Field(default_factory=list)
    xref: list[str] = Field(default_factory=list)
    antonym: list[str] = Field(default_factory=list)
    lsource: list[dict[str, Any]] = Field(default_factory=list)

    def all_tags(self) -> list[str]:
        """
        Return every tag code attached to the sense

        Returns:
            The pos, field, misc and dialect codes concatenated in that order
        """
        return [*self.pos, *self.field, *self.misc, *self.dialect]

    def expand_tags(self, labels: dict[str, str]) -> list[str]:
        """
        Resolve the sense's tag codes to human descriptions

        Args:
            labels (dict[str, str]): A code to description map, such as the one
                on [`LookupResult.labels`][kotobase.db.dtos.LookupResult]

        Returns:
            One description per tag code, falling back to the raw code when it
                isn't present in the map
        """
        return [labels.get(code, code) for code in self.all_tags()]


class KanjiFormDTO(SafeORMModel):
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
    info: list[str] = Field(default_factory=list)
    priority: list[str] = Field(default_factory=list)

    @property
    def key(self) -> str:
        """
        Return the lookup key for this kanji form

        Returns:
            The kanji spelling text
        """
        return self.text


class KanaFormDTO(SafeORMModel):
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
    restrictions: list[str] = Field(default_factory=list)
    info: list[str] = Field(default_factory=list)
    priority: list[str] = Field(default_factory=list)

    @property
    def key(self) -> str:
        """
        Return the lookup key for this kana form

        Returns:
            The kana reading text
        """
        return self.text


class JMDictEntryDTO(SafeORMModel):
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
    kanji: list[KanjiFormDTO] = Field(default_factory=list)
    kana: list[KanaFormDTO] = Field(default_factory=list)
    senses: list[SenseDTO] = Field(default_factory=list)

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

    @property
    def key(self) -> str:
        """
        Return the lookup key for this entry

        Returns:
            The entry's headword
        """
        return self.headword

    def common_kanji(self) -> list[KanjiFormDTO]:
        """
        Return only the written forms flagged common

        Returns:
            The kanji forms whose `is_common` is True
        """
        return [form for form in self.kanji if form.is_common]

    def common_kana(self) -> list[KanaFormDTO]:
        """
        Return only the reading forms flagged common

        Returns:
            The kana forms whose `is_common` is True
        """
        return [form for form in self.kana if form.is_common]

    def all_pos(self) -> list[str]:
        """
        Return the unique part-of-speech codes used across every sense

        Returns:
            The part-of-speech codes in first-seen order, without duplicates
        """
        seen: dict[str, None] = {}
        for sense in self.senses:
            for code in sense.pos:
                seen.setdefault(code, None)
        return list(seen)

    def senses_with_pos(self, code: str) -> list[SenseDTO]:
        """
        Return the senses that carry a given part-of-speech code

        Args:
            code (str): The part-of-speech tag code to match

        Returns:
            The senses whose `pos` contains the code
        """
        return [sense for sense in self.senses if code in sense.pos]


# --- JMnedict ---
class NameTranslationDTO(SafeORMModel):
    """
    A translation block of a `JMnedict` name

    Attributes:
        name_type (list[str]): Name type tag codes such as `place` or `surname`
        translations (list[str]): The translated names
        xref (list[str]): Cross references to related entries
    """

    name_type: list[str] = Field(default_factory=list)
    translations: list[str] = Field(
        default_factory=list, validation_alias="glosses"
    )
    xref: list[str] = Field(default_factory=list)

    @field_validator("translations", mode="before")
    @classmethod
    def _glosses_to_text(cls, value: Any) -> Any:
        """
        Flatten `JMnedictGloss` rows to their text when validating from ORM

        Args:
            value (Any): The raw `translations` input, a list of
                [`JMNedictGloss`][kotobase.db.models.JMNedictGloss]
                rows or strings

        Returns:
            A list of gloss strings, or the value unchanged when not a list
        """
        if isinstance(value, list):
            return [getattr(item, "text", item) for item in value]
        return value


class JMNeDictEntryDTO(SafeORMModel):
    """
    One `JMnedict` proper name entry

    Attributes:
        id (int): The JMnedict sequence number
        kanji (list[str]): Written forms of the name
        kana (list[str]): Reading forms of the name
        translations (list[NameTranslationDTO]): Translation blocks
    """

    id: int
    kanji: list[str] = Field(default_factory=list)
    kana: list[str] = Field(default_factory=list)
    translations: list[NameTranslationDTO] = Field(default_factory=list)

    @field_validator("kanji", "kana", mode="before")
    @classmethod
    def _forms_to_text(cls, value: Any) -> Any:
        """
        Flatten `JMnedict` kanji / kana rows to their text from ORM

        Args:
            value (Any): The raw form input, a list of
            [`JMnedictKanji`][kotobase.db.models.JMNedictKanji] /
            [`JMnedictKana`][kotobase.db.models.JMNedictKana]
            rows or strings

        Returns:
            A list of form strings, or the value unchanged when not a list
        """
        if isinstance(value, list):
            return [getattr(item, "text", item) for item in value]
        return value

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

    @property
    def key(self) -> str:
        """
        Return the lookup key for this name entry

        Returns:
            The name entry's headword
        """
        return self.headword


# --- Kanji ---
class KanjiDTO(SafeORMModel):
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
    onyomi: list[str] = Field(default_factory=list)
    kunyomi: list[str] = Field(default_factory=list)
    nanori: list[str] = Field(default_factory=list)
    pinyin: list[str] = Field(default_factory=list)
    korean: list[str] = Field(default_factory=list)
    meanings: list[str] = Field(default_factory=list)
    radicals: list[str] = Field(default_factory=list)
    dic_refs: dict[str, str] = Field(default_factory=dict)
    query_codes: dict[str, list[str]] = Field(default_factory=dict)
    codepoints: dict[str, str] = Field(default_factory=dict)
    variants: list[dict[str, Any]] = Field(default_factory=list)
    has_stroke_order: bool = False

    @property
    def key(self) -> str:
        """
        Return the lookup key for this kanji

        Returns:
            The kanji literal character
        """
        return self.literal

    def skip_codes(self) -> list[str]:
        """
        Return the SKIP query codes for the kanji

        Returns:
            The SKIP codes, or an empty list when none are recorded
        """
        return self.query_codes.get("skip", [])

    def four_corner_codes(self) -> list[str]:
        """
        Return the Four Corner query codes for the kanji

        Returns:
            The Four Corner codes, or an empty list when none are recorded
        """
        return self.query_codes.get("four_corner", [])

    def primary_onyomi(self) -> str | None:
        """
        Return the first on reading

        Returns:
            The first on reading, or None when there are none
        """
        return self.onyomi[0] if self.onyomi else None

    def primary_kunyomi(self) -> str | None:
        """
        Return the first kun reading

        Returns:
            The first kun reading, or None when there are none
        """
        return self.kunyomi[0] if self.kunyomi else None

    def is_joyo(self) -> bool:
        """
        Report whether the kanji is in the Joyo set

        Returns:
            True when the KanjiDic grade is 1 through 8
        """
        return self.grade is not None and self.grade <= 8


# --- Furigana, Sentences, JLPT ---
class FuriganaDTO(SafeORMModel):
    """
    Furigana segmentation for a spelling and reading pair

    Attributes:
        text (str): The written spelling
        reading (str): The full kana reading
        segments (list[dict]): Alignment of spelling spans to their readings
    """

    text: str
    reading: str
    segments: list[dict[str, Any]] = Field(default_factory=list)


class SentenceDTO(SafeORMModel):
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
    translations: list[str] = Field(default_factory=list)


class JLPTVocabDTO(SafeORMModel):
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

    @property
    def key(self) -> str:
        """
        Return the lookup key for this JLPT vocabulary item

        Returns:
            The headword, falling back to the reading, or an empty string
        """
        return self.word or self.reading or ""


class JLPTKanjiDTO(SafeORMModel):
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

    @property
    def key(self) -> str:
        """
        Return the lookup key for this JLPT kanji item

        Returns:
            The kanji character
        """
        return self.kanji


class JLPTGrammarDTO(SafeORMModel):
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
    examples: list[str] = Field(default_factory=list)


# --- Radicals, Audio ---
class RadicalDTO(SafeORMModel):
    """
    A search radical and its stroke count

    Attributes:
        radical (str): The radical character
        stroke_count (int | None): Number of strokes in the radical
    """

    radical: str
    stroke_count: int | None = None

    @property
    def key(self) -> str:
        """
        Return the lookup key for this radical

        Returns:
            The radical character
        """
        return self.radical


class AudioDTO(SafeORMModel):
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


# --- Aggregate Lookup Result ---
class LookupResult(BaseModel):
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
    entries: list[JMDictEntryDTO] = Field(default_factory=list)
    names: list[JMNeDictEntryDTO] = Field(default_factory=list)
    kanji: list[KanjiDTO] = Field(default_factory=list)
    furigana: list[FuriganaDTO] = Field(default_factory=list)
    jlpt_vocab: JLPTVocabDTO | None = None
    jlpt_kanji_levels: dict[str, int] = Field(default_factory=dict)
    jlpt_grammar: list[JLPTGrammarDTO] = Field(default_factory=list)
    sentences: list[SentenceDTO] = Field(default_factory=list)
    labels: dict[str, str] = Field(default_factory=dict)

    def has_entries(self) -> bool:
        """
        Report whether the result carries any dictionary entries

        Returns:
            True when at least one JMdict entry matched
        """
        return bool(self.entries)

    def has_names(self) -> bool:
        """
        Report whether the result carries any proper names

        Returns:
            True when at least one JMnedict name matched
        """
        return bool(self.names)

    def has_kanji(self) -> bool:
        """
        Report whether the result carries any kanji details

        Returns:
            True when at least one kanji profile is present
        """
        return bool(self.kanji)

    def has_sentences(self) -> bool:
        """
        Report whether the result carries any example sentences

        Returns:
            True when at least one Tatoeba sentence matched
        """
        return bool(self.sentences)

    def has_jlpt(self) -> bool:
        """
        Report whether the result carries any JLPT information

        Returns:
            True when a JLPT vocabulary entry or kanji level is present
        """
        return self.jlpt_vocab is not None or bool(self.jlpt_kanji_levels)


KotobaseDTO: TypeAlias = (
    GlossDTO
    | SenseDTO
    | KanjiFormDTO
    | KanaFormDTO
    | JMDictEntryDTO
    | NameTranslationDTO
    | JMNeDictEntryDTO
    | KanjiDTO
    | FuriganaDTO
    | SentenceDTO
    | JLPTVocabDTO
    | JLPTKanjiDTO
    | JLPTGrammarDTO
    | RadicalDTO
    | AudioDTO
    | LookupResult
)
"""
Represents any one of Kotobase's data transfer objects
"""
