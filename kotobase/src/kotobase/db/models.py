"""
Defines kotobase's database `SQLAlchemy 2.0` typed ORM schema

abstract: Schema
    - Preserves every field from the upstream sources

    - Includes the `JMdict` part of speech, register, field, dialect, sense
      information and priority tags + furigana segmentation from
      `jmdict_furigana`

    - Inclues the `JMNedict` kanji, kana, and translation information +
      furigana segmentation from `jmnedict_furigana`

    - Includes the full `KanjiDic2` reading, meaning and reference set,
      radical decompositions from `KRADFILE`, stroke orders from `KanjiVG`,
      and pronunciation audios from `kanjialive` (separate database, attached
      when present)

    - Includes japanese example sentence / translation pairs and audio
      provenance from `Tatoeba`

    - Includes grammar, kanji, and vocabulary information extracted from the
      `Tanos JLPT Lists`

info: Data Format
    - List shaped, read-only values such as tag code lists, cross references
      and furigana segments are stored in JSON columns using the SQLite `json1`
      extension

    - Anything that is searched or joined is normalized into its own table

    - Full text search is provided by `FTS5` virtual tables that the
      [`Build Pipeline`][kotobase.db.builder] creates at build time, so they
      are not declared here

note: Versioning
    - The schema is versioned by `db_meta['schema_version']`

    - Bump [`SCHEMA_VERSION`][kotobase.db.models.SCHEMA_VERSION] whenever the
      table layout changes so that a stale database can be detected
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import (
    JSON,
    ForeignKey,
    Index,
    LargeBinary,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)

SCHEMA_VERSION = 1
"""
Layout version stored in `db_meta` and checked by the read layer
"""


class Base(DeclarativeBase):
    """
    Declarative base class shared by every kotobase ORM model
    """


# --- JMdict (Japanese to English dictionary) ---
class JMDictEntry(Base):
    """
    A single JMdict dictionary entry

    Represents one `ent_seq` record from JMdict, which is the root of a
    Japanese to English entry. Its surface forms, readings and senses are
    attached through relationships

    Attributes:
        id (int): Primary key, the JMdict `ent_seq` sequence number
        is_common (bool): True when any form of the entry carries a priority
            marker that classifies it as common
        freq_rank (int | None): Frequency rank where a lower value is more
            frequent, or None when the entry has no priority information
        kanji (list[JMDictKanji]): Ordered kanji surface forms of the entry
        kana (list[JMDictKana]): Ordered kana readings of the entry
        senses (list[JMDictSense]): Ordered senses, each holding its glosses
    """

    __tablename__ = "jmdict_entry"

    id: Mapped[int] = mapped_column(primary_key=True)
    is_common: Mapped[bool] = mapped_column(default=False, index=True)
    freq_rank: Mapped[int | None] = mapped_column(index=True)

    kanji: Mapped[list[JMDictKanji]] = relationship(
        back_populates="entry",
        cascade="all, delete-orphan",
        order_by="JMDictKanji.position",
    )
    kana: Mapped[list[JMDictKana]] = relationship(
        back_populates="entry",
        cascade="all, delete-orphan",
        order_by="JMDictKana.position",
    )
    senses: Mapped[list[JMDictSense]] = relationship(
        back_populates="entry",
        cascade="all, delete-orphan",
        order_by="JMDictSense.position",
    )


class JMDictKanji(Base):
    """
    A kanji (written) surface form of a JMdict entry

    Attributes:
        id (int): Primary key row identifier
        entry_id (int): Foreign key to
            [JMDictEntry][kotobase.db.models.JMDictEntry]
        position (int): Zero based order of the form within the entry
        text (str): The kanji spelling
        is_common (bool): True when this form carries a common priority marker
        info (list[str]): Spelling information tag codes such as `iK` or
            `ateji`
        priority (list[str]): Priority code list such as `news1` or `ichi1`
        entry (JMDictEntry): The owning entry
    """

    __tablename__ = "jmdict_kanji"

    id: Mapped[int] = mapped_column(primary_key=True)
    entry_id: Mapped[int] = mapped_column(
        ForeignKey("jmdict_entry.id"),
        index=True,
    )
    position: Mapped[int] = mapped_column(default=0)
    text: Mapped[str] = mapped_column(index=True)
    is_common: Mapped[bool] = mapped_column(default=False)
    info: Mapped[list[str]] = mapped_column(JSON, default=list)
    priority: Mapped[list[str]] = mapped_column(JSON, default=list)

    entry: Mapped[JMDictEntry] = relationship(back_populates="kanji")


class JMDictKana(Base):
    """
    A kana (reading) form of a JMdict entry

    Attributes:
        id (int): Primary key row identifier
        entry_id (int): Foreign key to
            [JMDictEntry][kotobase.db.models.JMDictEntry]
        position (int): Zero based order of the reading within the entry
        text (str): The kana reading
        is_common (bool): True when this reading carries a common priority
            marker
        no_kanji (bool): True when the reading is not a reading of any kanji
            form
        restrictions (list[str]): Kanji forms this reading is restricted to,
            empty when the reading applies to all kanji forms
        info (list[str]): Reading information tag codes such as `ik` or `ok`
        priority (list[str]): Priority code list such as `news1` or `ichi1`
        entry (JMDictEntry): The owning entry
    """

    __tablename__ = "jmdict_kana"

    id: Mapped[int] = mapped_column(primary_key=True)
    entry_id: Mapped[int] = mapped_column(
        ForeignKey("jmdict_entry.id"),
        index=True,
    )
    position: Mapped[int] = mapped_column(default=0)
    text: Mapped[str] = mapped_column(index=True)
    is_common: Mapped[bool] = mapped_column(default=False)
    no_kanji: Mapped[bool] = mapped_column(default=False)
    restrictions: Mapped[list[str]] = mapped_column(JSON, default=list)
    info: Mapped[list[str]] = mapped_column(JSON, default=list)
    priority: Mapped[list[str]] = mapped_column(JSON, default=list)

    entry: Mapped[JMDictEntry] = relationship(back_populates="kana")


class JMDictSense(Base):
    """
    A sense (one meaning) of a JMdict entry

    A sense groups one or more glosses that share the same part of speech and
    usage information

    note: Misc Tags
        The `misc` list carries `register` and `slang` markers such as `sl`
        (slang), `net-sl` (internet slang), `col` (colloquial) and `vulg`
        (vulgar)

    Attributes:
        id (int): Primary key row identifier
        entry_id (int): Foreign key to
            [`JMDictEntry`][kotobase.db.models.JMDictEntry]
        position (int): Zero based order of the sense within the entry
        pos (list[str]): Part of speech tag codes such as `n` or `v5r`
        field (list[str]): Field of application tag codes such as `comp` or
            `med`
        misc (list[str]): Miscellaneous register tag codes, see the note above
        dialect (list[str]): Dialect tag codes such as `ksb` for the Kansai
            dialect
        info (list[str]): Free text sense information notes
        xref (list[str]): Cross reference targets to related entries
        antonym (list[str]): Antonym references for the sense
        applies_to_kanji (list[str]): Kanji forms the sense is restricted to,
            empty when it applies to all kanji forms
        applies_to_kana (list[str]): Kana forms the sense is restricted to,
            empty when it applies to all kana forms
        lsource (list[dict]): Source language records, each holding the
            language, text, type and a wasei flag for loanwords
        entry (JMDictEntry): The owning entry
        glosses (list[JMDictGloss]): Ordered glosses belonging to the sense
    """

    __tablename__ = "jmdict_sense"

    id: Mapped[int] = mapped_column(primary_key=True)
    entry_id: Mapped[int] = mapped_column(
        ForeignKey("jmdict_entry.id"),
        index=True,
    )
    position: Mapped[int] = mapped_column(default=0)
    pos: Mapped[list[str]] = mapped_column(JSON, default=list)
    field: Mapped[list[str]] = mapped_column(JSON, default=list)
    misc: Mapped[list[str]] = mapped_column(JSON, default=list)
    dialect: Mapped[list[str]] = mapped_column(JSON, default=list)
    info: Mapped[list[str]] = mapped_column(JSON, default=list)
    xref: Mapped[list[str]] = mapped_column(JSON, default=list)
    antonym: Mapped[list[str]] = mapped_column(JSON, default=list)
    applies_to_kanji: Mapped[list[str]] = mapped_column(JSON, default=list)
    applies_to_kana: Mapped[list[str]] = mapped_column(JSON, default=list)
    lsource: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)

    entry: Mapped[JMDictEntry] = relationship(back_populates="senses")
    glosses: Mapped[list[JMDictGloss]] = relationship(
        back_populates="sense",
        cascade="all, delete-orphan",
        order_by="JMDictGloss.position",
    )


class JMDictGloss(Base):
    """
    A single gloss (translation) belonging to a JMdict sense

    Attributes:
        id (int): Primary key row identifier
        sense_id (int): Foreign key to
            [`JMDictSense`][kotobase.db.models.JMDictSense]
        position (int): Zero based order of the gloss within the sense
        lang (str): ISO 639 language code of the gloss, defaults to `eng`
        text (str): The translated text
        gender (str | None): Grammatical gender of the gloss when given
        gtype (str | None): Gloss type such as `lit`, `fig`, `expl` or `tm`
        sense (JMDictSense): The owning sense
    """

    __tablename__ = "jmdict_gloss"

    id: Mapped[int] = mapped_column(primary_key=True)
    sense_id: Mapped[int] = mapped_column(
        ForeignKey("jmdict_sense.id"),
        index=True,
    )
    position: Mapped[int] = mapped_column(default=0)
    lang: Mapped[str] = mapped_column(default="eng")
    text: Mapped[str] = mapped_column(Text)
    gender: Mapped[str | None] = mapped_column()
    gtype: Mapped[str | None] = mapped_column()

    sense: Mapped[JMDictSense] = relationship(back_populates="glosses")

    __table_args__ = (Index("ix_jmdict_gloss_text", "text"),)


# --- JMnedict (Proper Names) ---
class JMnedictEntry(Base):
    """
    A JMnedict proper name entry

    Attributes:
        id (int): Primary key, the JMnedict sequence number
        kanji (list[JMnedictKanji]): Kanji forms of the name
        kana (list[JMnedictKana]): Kana forms of the name
        translations (list[JMnedictTranslation]): Ordered translation blocks
    """

    __tablename__ = "jmnedict_entry"

    id: Mapped[int] = mapped_column(primary_key=True)

    kanji: Mapped[list[JMnedictKanji]] = relationship(
        back_populates="entry",
        cascade="all, delete-orphan",
    )
    kana: Mapped[list[JMnedictKana]] = relationship(
        back_populates="entry",
        cascade="all, delete-orphan",
    )
    translations: Mapped[list[JMnedictTranslation]] = relationship(
        back_populates="entry",
        cascade="all, delete-orphan",
        order_by="JMnedictTranslation.position",
    )


class JMnedictKanji(Base):
    """
    A kanji form of a JMnedict entry

    Attributes:
        id (int): Primary key row identifier
        entry_id (int): Foreign key to
            [`JMnedictEntry`][kotobase.db.models.JMnedictEntry]
        position (int): Zero based order of the form within the entry
        text (str): The kanji spelling of the name
        entry (JMnedictEntry): The owning entry
    """

    __tablename__ = "jmnedict_kanji"

    id: Mapped[int] = mapped_column(primary_key=True)
    entry_id: Mapped[int] = mapped_column(
        ForeignKey("jmnedict_entry.id"),
        index=True,
    )
    position: Mapped[int] = mapped_column(default=0)
    text: Mapped[str] = mapped_column(index=True)

    entry: Mapped[JMnedictEntry] = relationship(back_populates="kanji")


class JMnedictKana(Base):
    """
    A kana form of a JMnedict entry

    Attributes:
        id (int): Primary key row identifier
        entry_id (int): Foreign key to
            [`JMnedictEntry`][kotobase.db.models.JMnedictEntry]
        position (int): Zero based order of the form within the entry
        text (str): The kana reading of the name
        entry (JMnedictEntry): The owning entry
    """

    __tablename__ = "jmnedict_kana"

    id: Mapped[int] = mapped_column(primary_key=True)
    entry_id: Mapped[int] = mapped_column(
        ForeignKey("jmnedict_entry.id"),
        index=True,
    )
    position: Mapped[int] = mapped_column(default=0)
    text: Mapped[str] = mapped_column(index=True)

    entry: Mapped[JMnedictEntry] = relationship(back_populates="kana")


class JMnedictTranslation(Base):
    """
    A translation block of a JMnedict entry

    Each block records the kind of name and holds one or more translated
    glosses

    Attributes:
        id (int): Primary key row identifier
        entry_id (int): Foreign key to
            [JMnedictEntry][kotobase.db.models.JMnedictEntry]
        position (int): Zero based order of the block within the entry
        name_type (list[str]): Name type tag codes such as `place`, `surname`,
            `given` or `company`
        xref (list[str]): Cross reference targets to related entries
        entry (JMnedictEntry): The owning entry
        glosses (list[JMnedictGloss]): Ordered translated names in this block
    """

    __tablename__ = "jmnedict_translation"

    id: Mapped[int] = mapped_column(primary_key=True)
    entry_id: Mapped[int] = mapped_column(
        ForeignKey("jmnedict_entry.id"),
        index=True,
    )
    position: Mapped[int] = mapped_column(default=0)
    name_type: Mapped[list[str]] = mapped_column(JSON, default=list)
    xref: Mapped[list[str]] = mapped_column(JSON, default=list)

    entry: Mapped[JMnedictEntry] = relationship(back_populates="translations")
    glosses: Mapped[list[JMnedictGloss]] = relationship(
        back_populates="translation",
        cascade="all, delete-orphan",
        order_by="JMnedictGloss.position",
    )


class JMnedictGloss(Base):
    """
    A single translated name belonging to a JMnedict translation block

    Attributes:
        id (int): Primary key row identifier
        translation_id (int): Foreign key to
            [`JMnedictTranslation`][kotobase.db.models.JMnedictTranslation]
        position (int): Zero based order of the gloss within the block
        lang (str): ISO 639 language code of the gloss, defaults to `eng`
        text (str): The translated name text
        translation (JMnedictTranslation): The owning translation block
    """

    __tablename__ = "jmnedict_gloss"

    id: Mapped[int] = mapped_column(primary_key=True)
    translation_id: Mapped[int] = mapped_column(
        ForeignKey("jmnedict_translation.id"),
        index=True,
    )
    position: Mapped[int] = mapped_column(default=0)
    lang: Mapped[str] = mapped_column(default="eng")
    text: Mapped[str] = mapped_column(Text)

    translation: Mapped[JMnedictTranslation] = relationship(
        back_populates="glosses",
    )


# --- KanjiDic2 ---
class Kanji(Base):
    """
    A `KanjiDic2` character and its scalar attributes

    The repeating attributes of a character such as readings, meanings and
    references live in dedicated child tables that are reachable through the
    relationships below

    Attributes:
        literal (str): Primary key, the kanji character itself
        grade (int | None): School grade in which the kanji is taught
        stroke_count (int | None): Accepted stroke count
        freq (int | None): Newspaper frequency rank where a lower value is more
            frequent
        jlpt_old (int | None): Pre 2010 four level JLPT class from KanjiDic2
        rad_classical (int | None): Classical (Kangxi) radical number
        rad_nelson (int | None): Nelson radical number when it differs
        stroke_miscounts (list[int]): Alternative miscount stroke values
        readings (list[KanjiReading]): On, kun and foreign readings
        meanings (list[KanjiMeaning]): Meanings keyed by language
        nanori (list[KanjiNanori]): Name only readings
        dic_refs (list[KanjiDicRef]): External dictionary references
        query_codes (list[KanjiQueryCode]): Lookup codes such as SKIP
        variants (list[KanjiVariant]): Variant form references
        codepoints (list[KanjiCodepoint]): Character encoding codepoints
        strokes (KanjiStrokes | None): KanjiVG stroke order data when present
    """

    __tablename__ = "kanji"

    literal: Mapped[str] = mapped_column(primary_key=True)
    grade: Mapped[int | None] = mapped_column(index=True)
    stroke_count: Mapped[int | None] = mapped_column(index=True)
    freq: Mapped[int | None] = mapped_column(index=True)
    jlpt_old: Mapped[int | None] = mapped_column()
    rad_classical: Mapped[int | None] = mapped_column(index=True)
    rad_nelson: Mapped[int | None] = mapped_column()
    stroke_miscounts: Mapped[list[int]] = mapped_column(JSON, default=list)

    readings: Mapped[list[KanjiReading]] = relationship(
        back_populates="kanji",
        cascade="all, delete-orphan",
    )
    meanings: Mapped[list[KanjiMeaning]] = relationship(
        back_populates="kanji",
        cascade="all, delete-orphan",
    )
    nanori: Mapped[list[KanjiNanori]] = relationship(
        back_populates="kanji",
        cascade="all, delete-orphan",
    )
    dic_refs: Mapped[list[KanjiDicRef]] = relationship(
        back_populates="kanji",
        cascade="all, delete-orphan",
    )
    query_codes: Mapped[list[KanjiQueryCode]] = relationship(
        back_populates="kanji",
        cascade="all, delete-orphan",
    )
    variants: Mapped[list[KanjiVariant]] = relationship(
        back_populates="kanji",
        cascade="all, delete-orphan",
    )
    codepoints: Mapped[list[KanjiCodepoint]] = relationship(
        back_populates="kanji",
        cascade="all, delete-orphan",
    )
    strokes: Mapped[KanjiStrokes | None] = relationship(
        back_populates="kanji",
        cascade="all, delete-orphan",
        uselist=False,
    )


class KanjiReading(Base):
    """
    A reading of a kanji

    Attributes:
        id (int): Primary key row identifier
        literal (str): Foreign key to [`Kanji`][kotobase.db.models.Kanji]
        type (str): Reading type such as `ja_on`, `ja_kun`, `pinyin` or
            `korean_r`
        value (str): The reading text
        position (int): Zero based order of the reading for its type
        kanji (Kanji): The owning kanji
    """

    __tablename__ = "kanji_reading"

    id: Mapped[int] = mapped_column(primary_key=True)
    literal: Mapped[str] = mapped_column(
        ForeignKey("kanji.literal"),
        index=True,
    )
    type: Mapped[str] = mapped_column(index=True)
    value: Mapped[str] = mapped_column(index=True)
    position: Mapped[int] = mapped_column(default=0)

    kanji: Mapped[Kanji] = relationship(back_populates="readings")


class KanjiMeaning(Base):
    """
    A meaning of a kanji in a given language

    Attributes:
        id (int): Primary key row identifier
        literal (str): Foreign key to [`Kanji`][kotobase.db.models.Kanji]
        lang (str): ISO 639 language code of the meaning, defaults to `en`
        value (str): The meaning text
        position (int): Zero based order of the meaning for its language
        kanji (Kanji): The owning kanji
    """

    __tablename__ = "kanji_meaning"

    id: Mapped[int] = mapped_column(primary_key=True)
    literal: Mapped[str] = mapped_column(
        ForeignKey("kanji.literal"),
        index=True,
    )
    lang: Mapped[str] = mapped_column(default="en")
    value: Mapped[str] = mapped_column(Text)
    position: Mapped[int] = mapped_column(default=0)

    kanji: Mapped[Kanji] = relationship(back_populates="meanings")


class KanjiNanori(Base):
    """
    A nanori (name only) reading of a kanji

    Attributes:
        id (int): Primary key row identifier
        literal (str): Foreign key to [`Kanji`][kotobase.db.models.Kanji]
        value (str): The nanori reading text
        position (int): Zero based order of the nanori for the kanji
        kanji (Kanji): The owning kanji
    """

    __tablename__ = "kanji_nanori"

    id: Mapped[int] = mapped_column(primary_key=True)
    literal: Mapped[str] = mapped_column(
        ForeignKey("kanji.literal"),
        index=True,
    )
    value: Mapped[str] = mapped_column()
    position: Mapped[int] = mapped_column(default=0)

    kanji: Mapped[Kanji] = relationship(back_populates="nanori")


class KanjiDicRef(Base):
    """
    An external dictionary reference for a kanji

    Attributes:
        id (int): Primary key row identifier
        literal (str): Foreign key to [`Kanji`][kotobase.db.models.Kanji]
        type (str): Reference type such as `nelson_c`, `heisig` or `moro`
        value (str): The reference value within that dictionary
        extra (dict | None): Extra metadata, for example volume and page for
            Morohashi references
        kanji (Kanji): The owning kanji
    """

    __tablename__ = "kanji_dic_ref"

    id: Mapped[int] = mapped_column(primary_key=True)
    literal: Mapped[str] = mapped_column(
        ForeignKey("kanji.literal"),
        index=True,
    )
    type: Mapped[str] = mapped_column()
    value: Mapped[str] = mapped_column()
    extra: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    kanji: Mapped[Kanji] = relationship(back_populates="dic_refs")


class KanjiQueryCode(Base):
    """
    A lookup query code for a kanji

    Attributes:
        id (int): Primary key row identifier
        literal (str): Foreign key to [`Kanji`][kotobase.db.models.Kanji]
        type (str): Code type such as `skip`, `four_corner` or `deroo`
        value (str): The code value
        skip_misclass (str | None): SKIP misclassification kind when present
        kanji (Kanji): The owning kanji
    """

    __tablename__ = "kanji_query_code"

    id: Mapped[int] = mapped_column(primary_key=True)
    literal: Mapped[str] = mapped_column(
        ForeignKey("kanji.literal"),
        index=True,
    )
    type: Mapped[str] = mapped_column(index=True)
    value: Mapped[str] = mapped_column(index=True)
    skip_misclass: Mapped[str | None] = mapped_column()

    kanji: Mapped[Kanji] = relationship(back_populates="query_codes")


class KanjiVariant(Base):
    """
    A variant form reference for a kanji

    Attributes:
        id (int): Primary key row identifier
        literal (str): Foreign key to [`Kanji`][kotobase.db.models.Kanji]
        type (str): Encoding of the variant value such as `jis208`
        value (str): The variant reference value
        kanji (Kanji): The owning kanji
    """

    __tablename__ = "kanji_variant"

    id: Mapped[int] = mapped_column(primary_key=True)
    literal: Mapped[str] = mapped_column(
        ForeignKey("kanji.literal"),
        index=True,
    )
    type: Mapped[str] = mapped_column()
    value: Mapped[str] = mapped_column()

    kanji: Mapped[Kanji] = relationship(back_populates="variants")


class KanjiCodepoint(Base):
    """
    A character encoding codepoint of a kanji

    Attributes:
        id (int): Primary key row identifier
        literal (str): Foreign key to [`Kanji`][kotobase.db.models.Kanji]
        type (str): Codepoint type such as `ucs` or `jis208`
        value (str): The codepoint value in that encoding
        kanji (Kanji): The owning kanji
    """

    __tablename__ = "kanji_codepoint"

    id: Mapped[int] = mapped_column(primary_key=True)
    literal: Mapped[str] = mapped_column(
        ForeignKey("kanji.literal"),
        index=True,
    )
    type: Mapped[str] = mapped_column()
    value: Mapped[str] = mapped_column()

    kanji: Mapped[Kanji] = relationship(back_populates="codepoints")


# --- Radicals (KRADFILE and RADKFILE) ---
class Radical(Base):
    """
    A search radical and its stroke count, taken from RADKFILE

    Attributes:
        radical (str): Primary key, the radical character
        stroke_count (int | None): Number of strokes in the radical
    """

    __tablename__ = "radical"

    radical: Mapped[str] = mapped_column(primary_key=True)
    stroke_count: Mapped[int | None] = mapped_column(index=True)


class KanjiRadical(Base):
    """
    A kanji to radical decomposition edge, taken from KRADFILE

    Each row records that a kanji contains a given radical component. The pair
    of kanji and radical is unique

    Attributes:
        id (int): Primary key row identifier
        literal (str): The kanji that contains the radical
        radical (str): The radical component contained in the kanji
    """

    __tablename__ = "kanji_radical"

    id: Mapped[int] = mapped_column(primary_key=True)
    literal: Mapped[str] = mapped_column(index=True)
    radical: Mapped[str] = mapped_column(index=True)

    __table_args__ = (
        UniqueConstraint("literal", "radical", name="uq_kanji_radical"),
    )


# --- Furigana (JmdictFurigana) ---
class Furigana(Base):
    """
    Furigana segmentation for a spelling and reading pair

    Attributes:
        id (int): Primary key row identifier
        text (str): The written spelling, usually containing kanji
        reading (str): The full kana reading of the spelling
        segments (list[dict]): The JmdictFurigana segmentation, a list of
            `{"ruby": ..., "rt": ...}` records that align spans of the spelling
            with their readings, where the pair of text and reading is unique
    """

    __tablename__ = "furigana"

    id: Mapped[int] = mapped_column(primary_key=True)
    text: Mapped[str] = mapped_column(index=True)
    reading: Mapped[str] = mapped_column(index=True)
    segments: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)

    __table_args__ = (UniqueConstraint("text", "reading", name="uq_furigana"),)


# --- Stroke Order (KanjiVG) ---
class KanjiStrokes(Base):
    """
    KanjiVG stroke order data for a kanji

    note: Licensing
        Provenance and licensing for `KanjiVG` are recorded once in `db_meta`
        rather than on every row to keep the table small

    Attributes:
        literal (str): Primary key and foreign key to
            [`Kanji`][kotobase.db.models.Kanji]
        stroke_count (int | None): Number of strokes in the diagram
        svg (str): Serialized KanjiVG `<kanji>` group markup with the stroke
            paths, from which a consumer can render stroke order
        kanji (Kanji): The owning kanji
    """

    __tablename__ = "kanji_strokes"

    literal: Mapped[str] = mapped_column(
        ForeignKey("kanji.literal"),
        primary_key=True,
    )
    stroke_count: Mapped[int | None] = mapped_column()
    svg: Mapped[str] = mapped_column(Text)

    kanji: Mapped[Kanji] = relationship(back_populates="strokes")


# --- Tatoeba example sentences ---
class Sentence(Base):
    """
    A `Tatoeba` sentence in a single language

    A row is either a Japanese sentence or an English translation of one. The
    `lang` column distinguishes them

    Attributes:
        id (int): Primary key, the Tatoeba sentence identifier
        lang (str): ISO 639 language code of the sentence
        text (str): The sentence text
    """

    __tablename__ = "sentence"

    id: Mapped[int] = mapped_column(primary_key=True)
    lang: Mapped[str] = mapped_column(index=True)
    text: Mapped[str] = mapped_column(Text)


class SentenceLink(Base):
    """
    A translation link from a Japanese sentence to another sentence

    Attributes:
        id (int): Primary key row identifier
        source_id (int): Foreign key to the Japanese
            [`Sentence`][kotobase.db.models.Sentence]
        target_id (int): Foreign key to the translated
            [`Sentence`][kotobase.db.models.Sentence]
    """

    __tablename__ = "sentence_link"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(
        ForeignKey("sentence.id"),
        index=True,
    )
    target_id: Mapped[int] = mapped_column(
        ForeignKey("sentence.id"),
        index=True,
    )


# --- Audio (Kanji Alive Blobs + Provenance) ---
class Audio(Base):
    """
    A pronunciation audio clip together with its provenance

    note: Optional Audio Pack
        - The `data` column is filled only in the optional audio pack

        - In the core database, a row may instead carry a `url` that points at
          a remote clip, for example a `Tatoeba` recording

    Attributes:
        id (int): Primary key row identifier
        kind (str): What the clip pronounces, such as `kanji_word`,
            `kanji_reading` or `sentence`
        key (str): Lookup key for the clip, such as a kanji, a word or a
            sentence identifier
        reading (str | None): The reading the clip pronounces when relevant
        fmt (str | None): Audio container or codec such as `ogg` or `mp3`
        sample_rate (int | None): Sample rate of the clip in hertz
        data (bytes | None): Raw audio bytes when bundled in the audio pack
        url (str | None): Remote location of the clip when it is not bundled
        source (str): Name of the upstream source, such as `kanjialive`
        license (str | None): License identifier for the clip
        attribution (str | None): Required attribution text or link
    """

    __tablename__ = "audio"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(index=True)
    key: Mapped[str] = mapped_column(index=True)
    reading: Mapped[str | None] = mapped_column()
    fmt: Mapped[str | None] = mapped_column()
    sample_rate: Mapped[int | None] = mapped_column()
    data: Mapped[bytes | None] = mapped_column(LargeBinary)
    url: Mapped[str | None] = mapped_column()
    source: Mapped[str] = mapped_column()
    license: Mapped[str | None] = mapped_column()
    attribution: Mapped[str | None] = mapped_column()


# --- JLPT (Tanos Lists, shipped with the package) ---
class JlptVocab(Base):
    """
    A Tanos JLPT vocabulary item

    Attributes:
        id (int): Primary key row identifier
        level (int): JLPT level from 1 (hardest) to 5 (easiest)
        word (str | None): The headword, written with kanji when one exists and
            falling back to the kana reading otherwise
        reading (str | None): The kana reading of the headword
        meaning (str | None): The English meaning, with senses comma separated
    """

    __tablename__ = "jlpt_vocab"

    id: Mapped[int] = mapped_column(primary_key=True)
    level: Mapped[int] = mapped_column(index=True)
    word: Mapped[str | None] = mapped_column(index=True)
    reading: Mapped[str | None] = mapped_column(index=True)
    meaning: Mapped[str | None] = mapped_column(Text)


class JlptKanji(Base):
    """
    A Tanos JLPT kanji item

    Attributes:
        id (int): Primary key row identifier
        level (int): JLPT level from 1 (hardest) to 5 (easiest)
        kanji (str): The kanji character
        on_yomi (str | None): On readings, space separated
        kun_yomi (str | None): Kun readings, space separated
        meaning (str | None): The English meaning, with senses comma separated
    """

    __tablename__ = "jlpt_kanji"

    id: Mapped[int] = mapped_column(primary_key=True)
    level: Mapped[int] = mapped_column(index=True)
    kanji: Mapped[str] = mapped_column(index=True)
    on_yomi: Mapped[str | None] = mapped_column()
    kun_yomi: Mapped[str | None] = mapped_column()
    meaning: Mapped[str | None] = mapped_column(Text)


class JlptGrammar(Base):
    """
    A Tanos JLPT grammar point

    Note:
        The `formation` and `examples` columns are kept for forward
        compatibility. The current Tanos data does not populate them, so they
        are normally empty

    Attributes:
        id (int): Primary key row identifier
        level (int): JLPT level from 1 (hardest) to 5 (easiest)
        grammar (str): The grammar point itself
        formation (str | None): How the grammar point is formed when known
        examples (list[str]): Example sentences for the grammar point
    """

    __tablename__ = "jlpt_grammar"

    id: Mapped[int] = mapped_column(primary_key=True)
    level: Mapped[int] = mapped_column(index=True)
    grammar: Mapped[str] = mapped_column(index=True)
    formation: Mapped[str | None] = mapped_column()
    examples: Mapped[list[str]] = mapped_column(JSON, default=list)


# --- Tag Dictionary + Build Metadata ---
class Tag(Base):
    """
    An entity tag code and its human readable description

    Populated from the `JMdict` and `JMnedict` `<!ENTITY>` definitions so that
    codes such as `sl` (slang) or `ksb` (Kansai dialect) can be expanded to
    text

    Attributes:
        code (str): Primary key part, the tag code as it appears in the source
        category (str): Primary key part, the tag family such as `pos`, `misc`,
            `field`, `dialect` or `name_type`
        description (str): Human readable description of the tag
    """

    __tablename__ = "tag"

    code: Mapped[str] = mapped_column(primary_key=True)
    category: Mapped[str] = mapped_column(primary_key=True)
    description: Mapped[str] = mapped_column(Text)


class DbMeta(Base):
    """
    A build metadata key and value pair

    abstract: Contains
        - Schema Version
        - Build Date
        - Build Duration
        - Database Size
        - Version / Date Of Each Data Source

    Attributes:
        key (str): Primary key, the metadata name
        value (str | None): The metadata value, stored as text
    """

    __tablename__ = "db_meta"

    key: Mapped[str] = mapped_column(primary_key=True)
    value: Mapped[str | None] = mapped_column(Text)
