"""
Shared fixtures for the kotobase test suite

A tiny `SQLite` database is built from the `ORM` models into a temporary
cache directory, so the database-backed tests run anywhere, including in `CI`,
without the real multi-hundred-megabyte database or any network access

The `audio` table is dropped from the fixture to mirror the core database,
where audio lives only in the optional pack, so the audio-missing error path
is exercised faithfully
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from kotobase import Kotobase
from kotobase.db import connection, models
from kotobase.db.builder import config


def _populate(session: Session) -> None:
    """
    Insert a small, hand-picked set of rows covering the query paths

    Args:
        session (Session): A writable session into the fixture database
    """
    session.add_all(
        [
            models.JMDictEntry(
                id=1,
                is_common=True,
                freq_rank=1,
                kanji=[
                    models.JMDictKanji(
                        position=0,
                        text="日本語",
                        is_common=True,
                        priority=["news1"],
                    )
                ],
                kana=[
                    models.JMDictKana(
                        position=0, text="にほんご", is_common=True
                    )
                ],
                senses=[
                    models.JMDictSense(
                        position=0,
                        pos=["n"],
                        xref=["英語"],
                        glosses=[
                            models.JMDictGloss(
                                position=0,
                                lang="eng",
                                text="Japanese (language)",
                            )
                        ],
                    )
                ],
            ),
            models.JMDictEntry(
                id=2,
                is_common=True,
                kanji=[models.JMDictKanji(position=0, text="英語")],
                kana=[models.JMDictKana(position=0, text="えいご")],
                senses=[
                    models.JMDictSense(
                        position=0,
                        pos=["n"],
                        glosses=[
                            models.JMDictGloss(
                                position=0,
                                lang="eng",
                                text="English (language)",
                            )
                        ],
                    )
                ],
            ),
            models.JMnedictEntry(
                id=3,
                kanji=[models.JMnedictKanji(position=0, text="田中")],
                kana=[models.JMnedictKana(position=0, text="たなか")],
                translations=[
                    models.JMnedictTranslation(
                        position=0,
                        name_type=["surname"],
                        glosses=[
                            models.JMnedictGloss(position=0, text="Tanaka")
                        ],
                    )
                ],
            ),
            models.Kanji(
                literal="語",
                grade=2,
                stroke_count=14,
                freq=301,
                jlpt_old=4,
                readings=[
                    models.KanjiReading(type="ja_on", value="ゴ", position=0),
                    models.KanjiReading(
                        type="ja_kun", value="かた.る", position=1
                    ),
                ],
                meanings=[
                    models.KanjiMeaning(lang="en", value="word", position=0),
                    models.KanjiMeaning(
                        lang="en", value="language", position=1
                    ),
                ],
                query_codes=[
                    models.KanjiQueryCode(type="skip", value="1-7-7"),
                    models.KanjiQueryCode(type="four_corner", value="0166.1"),
                ],
                dic_refs=[models.KanjiDicRef(type="nelson_c", value="4374")],
                codepoints=[models.KanjiCodepoint(type="ucs", value="8a9e")],
                strokes=models.KanjiStrokes(
                    stroke_count=14, svg="<svg></svg>"
                ),
            ),
            models.Kanji(literal="言", grade=2, stroke_count=7),
            models.Kanji(literal="五", grade=1, stroke_count=4),
            models.Radical(radical="言", stroke_count=7),
            models.Radical(radical="五", stroke_count=4),
            models.Radical(radical="口", stroke_count=3),
            models.KanjiRadical(literal="語", radical="言"),
            models.KanjiRadical(literal="語", radical="五"),
            models.KanjiRadical(literal="語", radical="口"),
            models.KanjiRadical(literal="言", radical="言"),
            models.KanjiRadical(literal="五", radical="五"),
            models.JlptKanji(level=5, kanji="語", on_yomi="ゴ"),
            models.JlptVocab(level=5, word="日本語", reading="にほんご"),
            models.Sentence(id=1, lang="jpn", text="日本語を勉強する。"),
            models.Sentence(id=2, lang="eng", text="I study Japanese."),
            models.SentenceLink(source_id=1, target_id=2),
            models.Tag(code="n", category="pos", description="noun"),
            models.Tag(code="sl", category="misc", description="slang"),
            models.DbMeta(
                key="schema_version", value=str(models.SCHEMA_VERSION)
            ),
        ]
    )
    session.commit()


def _build_database() -> None:
    """
    Create and populate the fixture database in the active cache directory
    """
    config.ensure_dirs()
    path = config.db_path()
    engine = create_engine(f"sqlite:///{path}")
    models.Base.metadata.create_all(engine)
    # The core database has no `audio` table
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE audio"))
    with Session(engine) as session:
        _populate(session)
    engine.dispose()
    # Drop the cached read-only engine so it reopens the populated file
    connection.get_engine.cache_clear()
    connection.get_sessionmaker.cache_clear()


@pytest.fixture(scope="session")
def kb(
    tmp_path_factory: pytest.TempPathFactory,
) -> Iterator[Kotobase]:
    """
    Yield a Kotobase backed by a freshly built, tiny fixture database

    Yields:
        A Kotobase instance pointed at the temporary fixture database
    """
    cache = tmp_path_factory.mktemp("kotobase_cache")
    patch = pytest.MonkeyPatch()
    patch.setenv(config.ENV_CACHE_DIR, str(cache))
    connection.get_engine.cache_clear()
    connection.get_sessionmaker.cache_clear()
    _build_database()
    try:
        yield Kotobase()
    finally:
        connection.get_engine.cache_clear()
        connection.get_sessionmaker.cache_clear()
        patch.undo()
