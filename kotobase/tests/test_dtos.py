"""
Tests for the pure, data-facing DTO methods that carry real logic

Trivial accessors and the ORM-to-DTO mapping are covered through the API
tests. These focus on the methods with branching or aggregation logic
"""

from __future__ import annotations

from kotobase.db.dtos import JMDictEntryDTO, KanjiDTO, SenseDTO


def test_all_pos_dedupes_and_preserves_order() -> None:
    """
    all_pos unions the senses' pos codes, keeping first-seen order
    """
    entry = JMDictEntryDTO.model_validate(
        {
            "id": 1,
            "senses": [
                {"pos": ["n", "vs"]},
                {"pos": ["vs", "adj-na"]},
            ],
        }
    )
    assert entry.all_pos() == ["n", "vs", "adj-na"]


def test_sense_expand_tags_falls_back_to_code() -> None:
    """
    expand_tags maps known codes and leaves unknown ones unchanged
    """
    sense = SenseDTO.model_validate({"pos": ["n"], "misc": ["sl"]})
    assert sense.expand_tags({"n": "noun"}) == ["noun", "sl"]


def test_kanji_is_joyo_boundary() -> None:
    """
    is_joyo is true for KanjiDic grades 1-8 and false beyond or absent
    """
    assert KanjiDTO.model_validate({"literal": "x", "grade": 8}).is_joyo()
    assert not KanjiDTO.model_validate({"literal": "x", "grade": 9}).is_joyo()
    assert not KanjiDTO.model_validate({"literal": "x"}).is_joyo()
