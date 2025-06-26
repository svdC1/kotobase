"""
This module defines the `kotobase` datatypes representing
information from the different data sources.
"""

from __future__ import annotations
from dataclasses import asdict, dataclass, field
import json
from typing import (Any,
                    List,
                    Dict,
                    Iterable,
                    Callable,
                    Optional)
from kotobase.db import models as orm


class Serializable:
    """
    Base class for adding `to_dict` and `to_json`
    methods for all dataclasses.
    """

    def to_dict(self) -> Dict[str, Any]:
        """
        Return DTO as a python dictionary by calling `asdict` on dataclass

        Returns:
          Dict[str, Any]: DTO information as a python dict
        """
        return asdict(self, dict_factory=dict)

    def to_json(self, **json_kwargs) -> str:
        """
        Return DTO in json format by calling `json.dumps` on the
        `to_dict` method.

        Args:
          **json_kwargs (dict): Keyword arguments for `json.dumps`

        Returns:
          str: The object in JSON string format
        """
        json_kwargs.update(obj=self.to_dict(),
                           ensure_ascii=False,
                           separators=(",", ":")
                           )
        return json.dumps(**json_kwargs)

    def __iter__(self):
        yield from self.to_dict().items()

# DTOS


@dataclass(slots=True)
class JMDictEntryDTO(Serializable):
    """
    A Python Dataclass object representing a JMDict Entry.

    Args:
      id: Integer Database Entry ID.
      kana: List of Strings representing Kana Readings.
      kanji: List of Strings representig existing Kanji in Entry.
      senses: List of Dicts in format {'id':int,'order':int,'gloss':str}
              representing Entry senses.
    """
    id: int
    kana: List[str] = field(default_factory=list)
    kanji: List[str] = field(default_factory=list)
    senses: List[Dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class JMNeDictEntryDTO(Serializable):
    """
    A Python Dataclass object representing a JMNeDict Entry.

    Args:
      id: Integer Database Entry ID.
      kana: List of Strings representing Kana Readings.
      kanji: List of Strings representig existing Kanji in Entry.
      translation_type: String representing type of Entry.
      gloss: List of strings representing glosses of Entry.
    """
    id: int
    kana: List[str] = field(default_factory=list)
    kanji: List[str] = field(default_factory=list)
    translation_type: str = ""
    gloss: List[str] = field(default_factory=list)


@dataclass(slots=True)
class JLPTVocabDTO(Serializable):
    """
    A Python Dataclass object representing an entry of
    Tanos JLPT Vocabulary list.

    Args:
      id: Integer Database Entry ID.
      level: Integer representing in which JLPT level the Entry exists.
      kanji: String representing Entry Kanji
      hiragana: String representing Entry kana reading.
      english: String representing Entry english translation
    """
    id: int
    level: int
    kanji: str
    hiragana: str
    english: str


@dataclass(slots=True)
class JLPTKanjiDTO(Serializable):
    """
    A Python Dataclass object representing an entry of
    Tanos JLPT Kanji list.

    Args:
      id: Integer Database Entry ID.
      level: Integer representing in which JLPT level the Entry exists.
      kanji: String representing Entry Kanji
    """
    id: int
    level: int
    kanji: str


@dataclass(slots=True)
class JLPTGrammarDTO(Serializable):
    """
    A Python Dataclass object representing an entry of
    Tanos JLPT Grammar list.

    Args:
      id: Integer Database Entry ID.
      level: Integer representing in which JLPT level the Entry exists.
      grammar: String representing grammar point.
      formation: String representing grammar point formation pattern.
      examples: List of strings containing grammar point examples.
    """
    id: int
    level: int
    grammar: str
    formation: str
    examples: List[str] = field(default_factory=list)


@dataclass(slots=True)
class KanjiDTO(Serializable):
    """
    A Python Dataclass object representing an entry of
    KANJIDIC2.

    Args:
      literal: String of Kanji Literal
      grade: Optional Integer of Japanese Grade in which Kanji is learned
      stroke_count: Integer representing number of strokes in handwriting.
      meanings: List of String representing known meanings.
      onyomi: List of strings representing on readings.
      kunyomi: List of strings representing kun readings.
      jlpt_kanjidic: Optional Integer representing JLPT level in KANJIDIC2
      jlpt_tanos: Optional Integer representing JLPT level in Tanos list.
    """
    literal: str
    grade: Optional[int]
    stroke_count: int
    meanings: List[str]
    onyomi: List[str]
    kunyomi: List[str]
    jlpt_kanjidic: Optional[int]
    jlpt_tanos: Optional[int]


@dataclass(slots=True)
class SentenceDTO(Serializable):
    """
    A Python Dataclass object representing an example
    sentence from the Tatoeba project.
    Args:
      id: Integer Database Entry ID.
      text: String of example.
    """
    id: int
    text: str


@dataclass(slots=True)
class LookupResult(Serializable):
    """
    A Python Dataclass object which aggreates results
    of all database queries.

    Args:
      word: String of the looked up word.
      entries: List containing found entries in the form of JMDictEntryDTO or
               JMNeDictEntryDTO objects.
      kanji: List containing found kanji in the form of KanjiDTO objects.
      jlpt_vocab: Optional JLPTVocabDTO object.
      jlpt_kanji_levels: Dictionary with kanji levels from Tanos Lists.
      jlpt_grammar: List of JLPTGrammarDTO objects.
      examples: List of SentenceDTO objects.
    """
    word: str
    entries: List[JMDictEntryDTO | JMNeDictEntryDTO]
    kanji: List[KanjiDTO]
    jlpt_vocab: Optional[JLPTVocabDTO]
    jlpt_kanji_levels: Dict[str, int]
    jlpt_grammar: List[JLPTGrammarDTO]
    examples: List[SentenceDTO]

    def has_jlpt(self) -> bool:
        """
        Convenience function for checking if the result contains JLPT
        information

        Returns:
          bool: True if JLPT is present, False otherwise
        """
        return self.jlpt_vocab is not None or bool(self.jlpt_kanji_levels)

# Helpers


def _split_list(field: Optional[str],
                sep: str = ";"
                ) -> List[str]:
    """
    Split data fields which are stored as strings, like meanings or
    readings, into a list.

    Args:
      field (str, optional): Field to split.
      sep (str): Which separator to split on.

    Returns:
      List[str]: The list of split data.
    """
    if not field:
        return []
    if isinstance(field, (list, tuple)):
        return list(field)
    return [x.strip() for x in field.split(sep) if x.strip()]


# Mappers

def map_jmdict(entry: orm.JMDictEntry) -> JMDictEntryDTO:
    """
    Map Raw JMDictEntry database row to a Python DTO.

    Args:
      entry (JMDictEntry): SQLAlchemy Table object

    Returns:
      JMDictEntryDTO: Python DTO

    """
    return JMDictEntryDTO(
        id=entry.id,
        kana=[k.text for k in entry.kana],
        kanji=[k.text for k in entry.kanji],
        senses=[
            {
                "order": s.order,
                "pos":   s.pos,
                "gloss": s.gloss,
            }
            for s in entry.senses
        ],
    )


def map_jmnedict(entry: orm.JMnedictEntry) -> JMNeDictEntryDTO:
    """
    Map Raw JMNeDictEntry database row to a Python DTO.

    Args:
      entry (JMneDictEntry): SQLAlchemy Table object

    Returns:
      JMNeDictEntryDTO: Python DTO

    """
    return JMNeDictEntryDTO(
        id=entry.id,
        kana=_split_list(entry.kana,  sep=";"),
        kanji=_split_list(entry.kanji, sep=";"),
        translation_type=entry.translation_type,
        gloss=_split_list(entry.translation, sep=";"),
    )

# ──────────────────────────────────────────────────────────────────────────
#  JLPT (Tanos lists)
# ──────────────────────────────────────────────────────────────────────────


def map_jlpt_vocab(row: orm.JlptVocab) -> JLPTVocabDTO:
    """
    Map Raw JLPT Vocabulary database row to a Python DTO.

    Args:
      entry (JlptVocab): SQLAlchemy Table object

    Returns:
      JLPTVocabDTO: Python DTO

    """
    return JLPTVocabDTO(
        id=row.id,
        level=row.level,
        kanji=row.kanji,
        hiragana=row.hiragana,
        english=row.english,
    )


def map_jlpt_kanji(row: orm.JlptKanji) -> JLPTKanjiDTO:
    """
    Map Raw JLPT Kanji database row to a Python DTO.

    Args:
      entry (JlptKanji): SQLAlchemy Table object

    Returns:
      JLPTKanjiDTO: Python DTO

    """
    return JLPTKanjiDTO(
        id=row.id,
        level=row.level,
        kanji=row.kanji,
    )


def map_jlpt_grammar(row: orm.JlptGrammar) -> JLPTGrammarDTO:
    """
    Map Raw JLPT Grammar database row to a Python DTO.

    Args:
      entry (JlptGrammar): SQLAlchemy Table object

    Returns:
      JLPTGrammarDTO: Python DTO

    """
    return JLPTGrammarDTO(
        id=row.id,
        level=row.level,
        grammar=row.grammar,
        formation=row.formation,
        examples=_split_list(row.examples, sep="|"),
    )


def map_kanjidic(
    row: orm.Kanjidic,
    *,
    jlpt_tanos_level: Optional[int] = None,
) -> KanjiDTO:
    """
    Map Raw KANJIDIC2 database row to a Python DTO.

    Args:
      row (Kanjidic): SQLAlchemy Table object
      jlpt_tanos_level (int, optional): JLPT level extracted from Tanos lists
                                        if it exists.

    Returns:
      KanjiDTO: Python DTO
    """
    return KanjiDTO(
        literal=row.literal,
        grade=row.grade,
        stroke_count=row.stroke_count,
        meanings=_split_list(row.meanings, sep=";"),
        onyomi=_split_list(row.on_readings, sep=";"),
        kunyomi=_split_list(row.kun_readings, sep=";"),
        jlpt_kanjidic=row.jlpt,
        jlpt_tanos=jlpt_tanos_level,
    )


def map_sentence(row: orm.TatoebaSentence) -> SentenceDTO:
    """
    Map Raw Tatoeba exmaple sentences database row to a Python DTO.

    Args:
      entry (TatoebaSentence): SQLAlchemy Table object

    Returns:
      SentenceDTO: Python DTO
    """
    return SentenceDTO(
        id=row.id,
        text=row.text,
    )

# ──────────────────────────────────────────────────────────────────────────
#  Bulk convenience wrapper
# ──────────────────────────────────────────────────────────────────────────


def map_many(func: Callable,
             rows: Iterable
             ) -> List:
    """
    Apply any single-row mapper across any iterable while keeping return order.

    Args:
      func (Callable): The mapper function to apply
      rows (Iterable): The returned database rows

    Returns:
      list: List of the DTO objects returned by `func`
    """
    return [func(r) for r in rows]


__all__ = ["Serializable",
           "JMDictEntryDTO",
           "JMNeDictEntryDTO",
           "JLPTVocabDTO",
           "JLPTKanjiDTO",
           "JLPTGrammarDTO",
           "KanjiDTO",
           "SentenceDTO",
           "LookupResult",
           "_split_list",
           "map_jlpt_grammar",
           "map_jlpt_kanji",
           "map_jlpt_vocab",
           "map_jmdict",
           "map_jmnedict",
           "map_kanjidic",
           "map_many",
           "map_sentence"
           ]
