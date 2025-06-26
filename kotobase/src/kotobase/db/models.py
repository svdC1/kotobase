"""
This module defines the `kotobase` database schema with `SQLAlchemy`
"""

from sqlalchemy import (Column,
                        Integer,
                        String,
                        Text,
                        ForeignKey,
                        Index
                        )
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

# ––––––––––––––––– JMDict ––––––––––––––––


class JMDictEntry(Base):
    """
    Raw Database JMDictEntry Table

    Attributes:
      id (int): Row ID
      kanji (relationship): Relationship to JMDict Kanji Table
      kana (relationship): Relationship to JMDict Kana Table
      senses (relationship): Relationship to JMDict Senses Table
    """
    __tablename__ = "jmdict_entries"
    id = Column(
        Integer,
        primary_key=True
        )

    kanji = relationship(
        "JMDictKanji",
        back_populates="entry",
        cascade="all, delete-orphan",
        order_by="JMDictKanji.order",
        )
    kana = relationship(
        "JMDictKana",
        back_populates="entry",
        cascade="all, delete-orphan",
        order_by="JMDictKana.order",
        )
    senses = relationship(
        "JMDictSense",
        back_populates="entry",
        cascade="all, delete-orphan",
        order_by="JMDictSense.order",
        )


class JMDictKanji(Base):
    """
    Raw Database JMDict Kanji Table

    Attributes:
      id (int): Row ID
      entry_id (int): Foreign key to JMDictEntry id
      order (id): Order of appearence
      text (str): Kanji Text
      entry (relationship): Relationship to JMDict Entries
    """
    __tablename__ = "jmdict_kanji"
    id = Column(
        Integer,
        primary_key=True
        )
    entry_id = Column(
        Integer,
        ForeignKey("jmdict_entries.id"),
        index=True,
        nullable=False
        )
    order = Column(
        Integer
        )
    text = Column(
        String,
        nullable=False
        )

    entry = relationship("JMDictEntry",
                         back_populates="kanji")

    __table_args__ = (Index("ix_jmdict_kanji_text", "text"),)


class JMDictKana(Base):
    """
    Raw Database JMDictEntry Kana Table.

    Attributes:
      id (int): Row ID
      entry_id (int): Foreign key to JMDictEntry id
      order (id): Order of appearence
      text (str): Kana Text
      entry (relationship): Relationship to JMDict Entries
    """
    __tablename__ = "jmdict_kana"
    id = Column(
        Integer,
        primary_key=True
        )
    entry_id = Column(
        Integer,
        ForeignKey("jmdict_entries.id"),
        index=True,
        nullable=False
        )
    order = Column(
        Integer
        )
    text = Column(
        String,
        nullable=False
        )

    entry = relationship(
        "JMDictEntry",
        back_populates="kana"
        )

    __table_args__ = (Index("ix_jmdict_kana_text", "text"),)


class JMDictSense(Base):
    """
    Raw Database JMDict Senses Table.

    Attributes:
      id (int): Row ID
      entry_id (int): Foreign Key to JMDict Entries Table ID
      order (int): Integer representing precedence of sense.
      pos (str): Part of Speech the entry sense belongs to.
      gloss (str): Gloss of the entry.
      entry (relationship): Relationship to JMDict Entries Table
    """
    __tablename__ = "jmdict_senses"
    id = Column(
        Integer,
        primary_key=True
        )
    entry_id = Column(
        Integer,
        ForeignKey("jmdict_entries.id"),
        index=True,
        nullable=False
        )
    order = Column(
        Integer
        )
    pos = Column(
        String
        )
    gloss = Column(
        Text
        )

    entry = relationship("JMDictEntry", back_populates="senses")

    __table_args__ = (Index("ix_jmdict_gloss", "gloss"),)

# ––––––––––– Optional FTS5 shadow table ––––––––––
# Only created when the build script detects sqlite3 and the "fts5" module.


class JMDictGlossFTS(Base):
    """
    FTS5 shadow table for entry sense gloss.

    Attributes:
      rowid (int): Row ID
      gloss (str): Entry sense gloss.
    """
    __tablename__ = "jmdict_gloss_fts"
    __table_args__ = {"sqlite_with_rowid": False}
    rowid = Column(
        Integer,
        primary_key=True
        )
    gloss = Column(
        Text
        )

# ––––––––––––––––– JMnedict ––––––––––––––––


class JMnedictEntry(Base):
    """
    Raw Database JMNeDictEntry Table.

    Attributes:
      id (int): Row ID
      kanji (str): Kanji text
      kana (str): Kana text
      translation_type (str): Type of entry.
      translation (Text): English text
    """
    __tablename__ = "jmnedict_entries"
    id = Column(
        Integer,
        primary_key=True
        )
    kanji = Column(
        String,
        index=True
        )
    kana = Column(
        String,
        index=True
        )
    tr_type = Column(
        String(8)
    )
    english = Column(
        Text
        )

# ––––––––––––––––– KANJIDIC2 ––––––––––––––––


class Kanjidic(Base):
    """
    Raw Database KANJIDIC2 Table.

    Attributes:
      literal (str): Kanji Literal
      grade (int): Japanese Grade in which Kanji is taught.
      stroke_count (int): Number of strokes in handwriting.
      jlpt (int): KANJIDIC2 JLPT classification.
      on_readings (str): On'yomi of Kanji
      kun_readings (str): Kun'yomi of Kanji
      meanings (str): List of meanings.
    """
    __tablename__ = "kanjidic"
    literal = Column(
        String,
        primary_key=True
        )
    grade = Column(
        Integer
        )
    stroke_count = Column(
        Integer
        )
    jlpt = Column(
        Integer
        )
    on_readings = Column(
        String
        )
    kun_readings = Column(
        String
        )
    meanings = Column(
        String
        )


class TatoebaSentence(Base):
    """
    Raw Database Tatoeba Example Sentences Table.

    Attributes:
      id (int): Row ID
      text (Text): The example sentence entry.
    """
    __tablename__ = 'tatoeba_sentences'
    id = Column(Integer,
                primary_key=True
                )
    text = Column(Text)


class JlptVocab(Base):
    """
    Raw Database Tanos JLPT Vocab List Table.

    Attributes:
      id (int): Row ID
      level (int): JLPT Level of the entry
      kanji (str): Kanji contained in the entry
      hiragana (str): Kana Reading of the entry
      english (Text): English translation of the entry
    """
    __tablename__ = 'jlpt_vocab'
    id = Column(Integer,
                primary_key=True
                )
    level = Column(Integer)
    kanji = Column(String)
    hiragana = Column(String)
    english = Column(Text)


class JlptKanji(Base):
    """
    Raw Database Tanos JLPT Kanji Table.

    Attributes:
      id (int): Row ID
      level (int): Tanos JLPT level of Kanji
      kanji (str): Literal Kanji
      on_yomi (str): On'yomi of the Kanji
      kun_yomi (str): Kun'yomi of the Kanji
      english (str): English translation
    """
    __tablename__ = 'jlpt_kanji'
    id = Column(Integer,
                primary_key=True
                )
    level = Column(Integer)
    kanji = Column(String)
    on_yomi = Column(String)
    kun_yomi = Column(String)
    english = Column(Text)


class JlptGrammar(Base):
    """
    Raw Database Tanos JLPT Grammar Table.

    Attributes:
      id (int): Row ID
      level (int): JLPT level of grammar point
      grammar (str): Grammar point itself
      formation (str): General formation of grammar point
      examples (Text): List of examples containing grammar point
    """
    __tablename__ = 'jlpt_grammar'
    id = Column(Integer,
                primary_key=True
                )
    level = Column(Integer)
    grammar = Column(String)
    formation = Column(String)
    examples = Column(Text)


__all__ = ["Base",
           "JMDictEntry",
           "JMDictKanji",
           "JMDictKana",
           "JMDictSense",
           "JMnedictEntry",
           "Kanjidic",
           "TatoebaSentence",
           "JlptVocab",
           "JlptKanji",
           "JlptGrammar"
           ]
