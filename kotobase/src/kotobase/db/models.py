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
    __tablename__ = 'jmnedict_entries'
    id = Column(Integer,
                primary_key=True
                )
    kanji = Column(String)
    kana = Column(String)
    translation_type = Column(String)
    translation = Column(Text)


class Kanjidic(Base):
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
    __tablename__ = 'tatoeba_sentences'
    id = Column(Integer,
                primary_key=True
                )
    text = Column(Text)


class JlptVocab(Base):
    __tablename__ = 'jlpt_vocab'
    id = Column(Integer,
                primary_key=True
                )
    level = Column(Integer)
    kanji = Column(String)
    hiragana = Column(String)
    english = Column(Text)


class JlptKanji(Base):
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
