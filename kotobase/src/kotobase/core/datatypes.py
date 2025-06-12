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
        return asdict(self, dict_factory=dict)

    def to_json(self, **json_kwargs) -> str:
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
    id: int
    kana: List[str] = field(default_factory=list)
    kanji: List[str] = field(default_factory=list)
    senses: List[Dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class JMNeDictEntryDTO(Serializable):
    id: int
    kana: List[str] = field(default_factory=list)
    kanji: List[str] = field(default_factory=list)
    translation_type: str = ""
    gloss: List[str] = field(default_factory=list)
# ---- JLPT ---------------------------------------------------------------


@dataclass(slots=True)
class JLPTVocabDTO(Serializable):
    id: int
    level: int
    kanji: str
    hiragana: str
    english: str


@dataclass(slots=True)
class JLPTKanjiDTO(Serializable):
    id: int
    level: int
    kanji: str


@dataclass(slots=True)
class JLPTGrammarDTO(Serializable):
    id: int
    level: int
    grammar: str
    formation: str
    examples: List[str] = field(default_factory=list)

# ---- Kanjidic -----------------------------------------------------------


@dataclass(slots=True)
class KanjiDTO(Serializable):
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
    id: int
    text: str

# ---- Aggregate result ---------------------------------------------------


@dataclass(slots=True)
class LookupResult(Serializable):
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
    return JLPTVocabDTO(
        id=row.id,
        level=row.level,
        kanji=row.kanji,
        hiragana=row.hiragana,
        english=row.english,
    )


def map_jlpt_kanji(row: orm.JlptKanji) -> JLPTKanjiDTO:
    return JLPTKanjiDTO(
        id=row.id,
        level=row.level,
        kanji=row.kanji,
    )


def map_jlpt_grammar(row: orm.JlptGrammar) -> JLPTGrammarDTO:
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
