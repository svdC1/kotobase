from sqlalchemy import Column, Integer, String, Text, ForeignKey, Table
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

# --- Association Tables ---

jmdict_kanji_assoc = Table('jmdict_kanji_assoc',
                           Base.metadata,
                           Column('jmdict_id',
                                  Integer,
                                  ForeignKey('jmdict_entries.id')
                                  ),
                           Column('kanji_id',
                                  Integer,
                                  ForeignKey('jmdict_kanji.id')
                                  )
                           )

jmdict_kana_assoc = Table('jmdict_kana_assoc',
                          Base.metadata,
                          Column('jmdict_id',
                                 Integer,
                                 ForeignKey('jmdict_entries.id')
                                 ),
                          Column('kana_id',
                                 Integer,
                                 ForeignKey('jmdict_kana.id')
                                 )
                          )

# --- Schema Definition ---


class JMDictEntry(Base):
    """
    Raw Database JMDictEntry Table

    Args:
      id (int): Row ID
      kanji (relationship): Relationship to JMDict Kanji Table
      kana (relationship): Relationship to JMDict Kana Table
      senses (relationship): Relationship to JMDict Senses Table
    """
    __tablename__ = 'jmdict_entries'
    id = Column(Integer,
                primary_key=True
                )
    kanji = relationship("JMDictKanji",
                         secondary=jmdict_kanji_assoc,
                         back_populates="entries"
                         )
    kana = relationship("JMDictKana",
                        secondary=jmdict_kana_assoc,
                        back_populates="entries"
                        )
    senses = relationship("JMDictSense",
                          back_populates="entry",
                          order_by="JMDictSense.order"
                          )


class JMDictKanji(Base):
    """
    Raw Database JMDict Kanji Table

    Args:
      id (int): Row ID
      text (str): Kanji Text
      entries (relationship): Relationship to JMDict Entries
    """
    __tablename__ = 'jmdict_kanji'
    id = Column(Integer,
                primary_key=True
                )
    text = Column(String,
                  unique=True
                  )
    entries = relationship("JMDictEntry",
                           secondary=jmdict_kanji_assoc,
                           back_populates="kanji"
                           )


class JMDictKana(Base):
    """
    Raw Database JMDictEntry Kana Table.

    Args:
      id (int): Row ID
      text (string): Kana text
      entries (relationship): Relationship to JMDict Entry Table.
    """
    __tablename__ = 'jmdict_kana'
    id = Column(Integer,
                primary_key=True
                )
    text = Column(String,
                  unique=True
                  )
    entries = relationship("JMDictEntry",
                           secondary=jmdict_kana_assoc,
                           back_populates="kana"
                           )


class JMDictSense(Base):
    """
    Raw Database JMDict Senses Table.

    Args:
      id (int): Row ID
      entry_id (int): Foreign Key to JMDict Entries Table ID
      entry (relationship): Relationship to JMDict Entries Table
      order (int): Integer representing precedence of sense.
      pos (str): Part of Speech the entry sense belongs to.
      gloss (Text): Gloss of the entry.
    """
    __tablename__ = 'jmdict_senses'
    id = Column(Integer,
                primary_key=True
                )
    entry_id = Column(Integer,
                      ForeignKey('jmdict_entries.id')
                      )
    entry = relationship("JMDictEntry",
                         back_populates="senses"
                         )
    order = Column(Integer)
    pos = Column(String)
    gloss = Column(Text)


class JMnedictEntry(Base):
    """
    Raw Database JMNeDictEntry Table.

    Args:
      id (int): Row ID
      kanji (str): Kanji text
      kana (str): Kana text
      translation_type (str): Type of entry.
      translation (Text): English text
    """
    __tablename__ = 'jmnedict_entries'
    id = Column(Integer,
                primary_key=True
                )
    kanji = Column(String)
    kana = Column(String)
    translation_type = Column(String)
    translation = Column(Text)


class Kanjidic(Base):
    """
    Raw Database KANJIDIC2 Table.

    Args:
      id (int): Row ID
      literal (str): Kanji Literal
      grade (int): Japanese Grade in which Kanji is taught.
      stroke_count (int): Number of strokes in handwriting.
      jlpt (int): KANJIDIC2 JLPT classification.
      on_readings (str): On'yomi of Kanji
      kun_readings (str): Kun'yomi of Kanji
      meanings (str): List of meanings.
    """
    __tablename__ = 'kanjidic'
    id = Column(Integer,
                primary_key=True
                )
    literal = Column(String,
                     unique=True
                     )
    grade = Column(Integer)
    stroke_count = Column(Integer)
    jlpt = Column(Integer)
    on_readings = Column(String)
    kun_readings = Column(String)
    meanings = Column(String)


class TatoebaSentence(Base):
    """
    Raw Database Tatoeba Example Sentences Table.

    Args:
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

    Args:
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

    Args:
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

    Args:
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
           "jmdict_kanji_assoc",
           "jmdict_kana_assoc",
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
