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


# ──────────────────────────────────────────────────────────────────────────
#  Serializable mix-in
# ──────────────────────────────────────────────────────────────────────────

class Serializable:
    """Adds to_dict / to_json to plain dataclasses."""

    def to_dict(self) -> Dict[str, Any]:
        """
        Return DTO as a python dictionary.
        """
        return asdict(self, dict_factory=dict)

    def to_json(self, **json_kwargs) -> str:
        """
        Return DTO in json format.
        """
        return json.dumps(
            self.to_dict(),
            ensure_ascii=False,
            separators=(",", ":"),
            **json_kwargs
        )

    def __iter__(self):
        yield from self.to_dict().items()


# ──────────────────────────────────────────────────────────────────────────
#  DTOs (defaults = empty to avoid accidental None)
# ──────────────────────────────────────────────────────────────────────────

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
# ---- JLPT ---------------------------------------------------------------


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

# ---- Kanjidic -----------------------------------------------------------


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

# ---- Tatoeba ------------------------------------------------------------


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

# ---- Aggregate result ---------------------------------------------------


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
        return self.jlpt_vocab is not None or bool(self.jlpt_kanji_levels)

# ──────────────────────────────────────────────────────────────────────────
#  Low-level helpers
# ──────────────────────────────────────────────────────────────────────────


def _split_list(field: Optional[str], sep: str = ";") -> List[str]:
    """
    Some tables (e.g. Kanjidic) store a *semi-colon* or *comma* separated
    string for readings / meanings.  Make sure we always return a list.
    """
    if not field:
        return []
    if isinstance(field, (list, tuple)):
        return list(field)
    return [x.strip() for x in field.split(sep) if x.strip()]


# ──────────────────────────────────────────────────────────────────────────
#  JMdict & JMnedict
# ──────────────────────────────────────────────────────────────────────────

def map_jmdict(entry: orm.JMDictEntry) -> JMDictEntryDTO:
    """
    Map Raw JMDictEntry database row to a Python DTO.
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
    """
    return JLPTKanjiDTO(
        id=row.id,
        level=row.level,
        kanji=row.kanji,
    )


def map_jlpt_grammar(row: orm.JlptGrammar) -> JLPTGrammarDTO:
    """
    Map Raw JLPT Grammar database row to a Python DTO.
    """
    return JLPTGrammarDTO(
        id=row.id,
        level=row.level,
        grammar=row.grammar,
        formation=row.formation,
        examples=_split_list(row.examples, sep="|"),
    )


# ──────────────────────────────────────────────────────────────────────────
#  KANJIDIC  (with *optional* JLPT-Tanos overlay)
# ──────────────────────────────────────────────────────────────────────────

def map_kanjidic(
    row: orm.Kanjidic,
    *,
    jlpt_tanos_level: Optional[int] = None,
) -> KanjiDTO:
    """
    Map Raw KANJIDIC2 database row to a Python DTO.
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


# ──────────────────────────────────────────────────────────────────────────
#  Tatoeba sentences
# ──────────────────────────────────────────────────────────────────────────

def map_sentence(row: orm.TatoebaSentence) -> SentenceDTO:
    """
    Map Raw Tatoeba exmaple sentences database row to a Python DTO.
    """
    return SentenceDTO(
        id=row.id,
        text=row.text,
    )

# ──────────────────────────────────────────────────────────────────────────
#  Bulk convenience wrapper
# ──────────────────────────────────────────────────────────────────────────


def map_many(func: Callable, rows: Iterable) -> List:
    """Apply any single-row mapper across any iterable, keep return order."""
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
