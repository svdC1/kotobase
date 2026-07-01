"""
Database-backed tests for the public Kotobase API

These run against the tiny fixture database from conftest
"""

from __future__ import annotations

import pytest

from kotobase import APIError, AudioDatabaseNotFoundError, Kotobase


def test_lookup_aggregates_sources(kb: Kotobase) -> None:
    """
    A comprehensive lookup returns the entry and its kanji
    """
    result = kb.lookup("日本語")
    assert result.has_entries()
    assert result.entries[0].headword == "日本語"
    assert result.has_kanji()
    assert any(k.literal == "語" for k in result.kanji)


def test_kanji_orm_mapping_derives_fields(kb: Kotobase) -> None:
    """
    KanjiDTO is assembled from several relationships and injected data
    """
    kanji = kb.kanji("語")
    assert kanji is not None
    assert kanji.onyomi == ["ゴ"]
    assert kanji.kunyomi == ["かた.る"]
    assert kanji.meanings == ["word", "language"]
    assert kanji.query_codes["skip"] == ["1-7-7"]
    assert kanji.dic_refs["nelson_c"] == "4374"
    assert kanji.codepoints["ucs"] == "8a9e"
    assert kanji.has_stroke_order is True
    assert sorted(kanji.radicals) == ["五", "口", "言"]
    assert kanji.jlpt_tanos == 5


def test_serialization_keeps_japanese(kb: Kotobase) -> None:
    """
    A DTO built from the database serializes Japanese text verbatim
    """
    dumped = kb.lookup("日本語").model_dump_json()
    assert "日本語" in dumped
    assert "\\u" not in dumped


def test_by_radicals_all_is_subset_of_any(kb: Kotobase) -> None:
    """
    `all` matches the intersection and `any` the union of radicals
    """
    every = kb.by_radicals(["言", "五"], match="all")
    some = kb.by_radicals(["言", "五"], match="any")
    assert [k.literal for k in every] == ["語"]
    assert {k.literal for k in some} == {"語", "言", "五"}


def test_by_radicals_accepts_radical_dtos(kb: Kotobase) -> None:
    """
    by_radicals reads the character off a RadicalDTO argument
    """
    radicals = {r.radical: r for r in kb.radicals()}
    matched = kb.by_radicals([radicals["言"], radicals["五"]], match="all")
    assert [k.literal for k in matched] == ["語"]


def test_words_with_kanji(kb: Kotobase) -> None:
    """
    words_with_kanji finds entries whose written form contains a kanji
    """
    headwords = {entry.headword for entry in kb.words_with_kanji("語")}
    assert headwords == {"日本語", "英語"}


def test_words_with_kanji_accepts_dto(kb: Kotobase) -> None:
    """
    words_with_kanji reads the literal off a KanjiDTO argument
    """
    kanji = kb.kanji("語")
    assert kanji is not None
    assert kb.words_with_kanji(kanji)


def test_sentences_with_kanji_aligns_translations(kb: Kotobase) -> None:
    """
    sentences_with_kanji returns matching sentences with their English
    translation
    """
    sentences = kb.sentences_with_kanji("語")
    assert sentences
    assert "I study Japanese." in sentences[0].translations


def test_resolve_references_follows_xref(kb: Kotobase) -> None:
    """
    resolve_references resolves an entry's xref code to its entry
    """
    entry = kb.lookup("日本語").entries[0]
    resolved = kb.resolve_references(entry)
    assert [entry.headword for entry in resolved] == ["英語"]


def test_names_flattens_jmnedict_rows(kb: Kotobase) -> None:
    """
    A proper-name lookup flattens kanji, kana and gloss rows to strings
    """
    names = kb.names("田中")
    assert names
    assert names[0].kanji == ["田中"]
    assert names[0].translations[0].translations == ["Tanaka"]


def test_expand_tags(kb: Kotobase) -> None:
    """
    expand_tags maps tag codes to their descriptions
    """
    assert kb.expand_tags(["sl", "n"]) == {"sl": "slang", "n": "noun"}


def test_jlpt_level(kb: Kotobase) -> None:
    """
    jlpt_level returns the vocabulary level of a listed word
    """
    assert kb.jlpt_level("日本語") == 5


def test_audio_without_pack_raises(kb: Kotobase) -> None:
    """
    Requesting audio bytes without the pack raises the typed error
    """
    with pytest.raises(AudioDatabaseNotFoundError):
        kb.audio_bytes("語")


def test_jlpt_list_rejects_bad_arguments(kb: Kotobase) -> None:
    """
    jlpt_list rejects an unknown kind or out-of-range level
    """
    with pytest.raises(APIError):
        kb.jlpt_list("bogus", 5)
    with pytest.raises(APIError):
        kb.jlpt_list("vocab", 9)


def test_by_radicals_rejects_bad_match(kb: Kotobase) -> None:
    """
    by_radicals rejects a match mode other than all or any
    """
    with pytest.raises(APIError):
        kb.by_radicals(["言"], match="nope")


def test_methods_accept_dtos(kb: Kotobase) -> None:
    """
    Key-taking methods read the lookup key off a DTO argument
    """
    entry = kb.lookup("日本語").entries[0]
    vocab = kb.jlpt_list("vocab", 5)[0]
    kanji = kb.kanji("語")
    assert kanji is not None
    assert kb.jlpt_level(entry) == 5
    assert kb.jlpt_level(vocab) == 5
    assert kb.kanji(kanji) is not None
    assert kb.sentences(entry)
