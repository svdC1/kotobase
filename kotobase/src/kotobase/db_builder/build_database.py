"""
This module defines the click command which builds the `kotobase.db` database
using SQLAlchemy.
"""

import json
import re
import os
import click
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import Session as SessionType
import time
import datetime
from textwrap import dedent
# --- Import from local modules ---
from kotobase.db_builder.config import (DATABASE_PATH,
                                        DB_BUILD_LOG_PATH,
                                        RAW_DATA_DIR,
                                        JMDICT_PATH,
                                        JMNEDICT_PATH,
                                        TATOEBA_PATH,
                                        JLPT_FOLDER,
                                        KANJIDIC2_PATH
                                        )
from kotobase.db_builder.download import main as download_data
from kotobase.db_builder.process_jmdict import parse_jmdict
from kotobase.db_builder.process_jmnedict import parse_jmnedict
from kotobase.db_builder.process_kanjidic import parse_kanjidic
from kotobase.db_builder.process_tatoeba import parse_tatoeba
from kotobase.db.models import (Base,
                                JMDictEntry,
                                JMDictKanji,
                                JMDictKana,
                                JMDictSense,
                                JMnedictEntry,
                                Kanjidic,
                                TatoebaSentence,
                                JlptVocab,
                                JlptKanji,
                                JlptGrammar,
                                )

# --- Database Setup ---
engine = create_engine(f'sqlite:///{DATABASE_PATH}')
Session = sessionmaker(bind=engine)


def create_database() -> None:
    """
    Click command helper which creates the database and all tables.
    """
    # Rebuild even when existent
    DATABASE_PATH.unlink(missing_ok=True)
    DATABASE_PATH.touch()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_kana_text ON jmdict_kana(text)"
            )
        conn.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS idx_kanji_text ON jmdict_kanji(text)"
            )
    click.echo("Database Created Successfully")


def populate_jmdict(session: SessionType) -> None:
    """
    Click command helper which populates JMDict tables in the database.

    Args:
      session (Session): SQLAlchemy Session object
    """
    click.echo("Populating JMDict Tables ...")
    with open(JMDICT_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    entries = []
    kanji_entries = []
    kana_entries = []
    sense_entries = []
    seen_ids: set[int] = set()
    with click.progressbar(data,
                           label="\nPreparing JMDict Data -> "
                           ) as bar:
        for item in bar:

            # Skip Duplicates
            if item['id'] in seen_ids:
                continue
            seen_ids.add(item['id'])
            entries.append({'id': item['id'],
                            'rank': item.get('rank', 99)
                            })

            # Kanji Readings
            for k in item.get('kanji', []):
                kanji_entries.append(
                    {'entry_id': item['id'],
                     'order': k.get('order', 0),
                     'text': k['text']
                     }
                    )

            # Kanji Readings
            for r in item.get('kana', []):
                kana_entries.append(
                    {'entry_id': item['id'],
                     'order': r.get('order', 0),
                     'text': r['text']
                     }
                    )
            # Senses
            for s in item.get('senses', []):
                sense_entries.append(
                    {'entry_id': item['id'],
                     'order': s.get('order'),
                     'pos': ", ".join(s.get('pos', [])),
                     'gloss': ", ".join(s.get('gloss', []))
                     }
                    )

    click.echo("\nInserting JMDict Data -> ")
    session.bulk_insert_mappings(JMDictEntry, entries)
    session.bulk_insert_mappings(JMDictKanji, kanji_entries)
    session.bulk_insert_mappings(JMDictKana, kana_entries)
    session.bulk_insert_mappings(JMDictSense, sense_entries)
    session.commit()
    click.echo("\nJMDict Tables Populated")


def populate_jmnedict(session: SessionType) -> None:
    """
    Click command helper which populates JMNeDict tables in the database.

    Args:
      session (Session): SQLAlchemy Session object
    """

    click.echo("Populating JMnedict Table ...")
    with open(JMNEDICT_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    entries = []
    with click.progressbar(data,
                           label="\nPreparing JMnedict Data -> "
                           ) as bar:
        for item in bar:
            types = [
                t for sublist in item['translations'] for t in sublist['type']
                ]
            translations = [
                t for sublist in item[
                    'translations'] for t in sublist['translation']
                ]
            entries.append(
                {'id': item['id'],
                 'kanji': ", ".join([k['text'] for k in item['kanji']]),
                 'kana': ", ".join([k['text'] for k in item['kana']]),
                 'translation_type': ", ".join(types),
                 'translation': ", ".join(translations)
                 }
                )

    click.echo("\nInserting JMnedict Entries -> ")
    session.bulk_insert_mappings(JMnedictEntry, entries)
    session.commit()
    click.echo("\nJMnedict Table Populated")


def populate_kanjidic(session: SessionType) -> None:
    """
    Click command helper which populates KANJIDIC table in the database.

    Args:
      session (Session): SQLAlchemy Session object
    """

    click.echo("Populating Kanjidic Table ...")
    with open(KANJIDIC2_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    entries = []
    with click.progressbar(data,
                           label="Preparing Kanjidic Data ->"
                           ) as bar:
        for item in bar:
            on_readings = [
                r['value'] for r in item['reading_meaning']['readings']
                if r['type'] == 'ja_on'
                ]
            kun_readings = [
                r['value'] for r in item['reading_meaning']['readings']
                if r['type'] == 'ja_kun'
                ]
            meanings = [
                m['value'] for m in item['reading_meaning']['meanings']
                if m['lang'] == 'en'
                ]

            entries.append(
                {'literal': item['literal'],
                 'grade': item.get('grade'),
                 'stroke_count': (
                     item['stroke_count'][0] if item['stroke_count'] else None
                     ),
                 'jlpt': item.get('jlpt'),
                 'on_readings': ", ".join(on_readings),
                 'kun_readings': ", ".join(kun_readings),
                 'meanings': ", ".join(meanings)
                 }
                )

    click.echo("\nInserting Kanjidic Entries -> ")
    session.bulk_insert_mappings(Kanjidic, entries)
    session.commit()
    click.echo("\nKanjidic Table Populated")


def populate_tatoeba(session: SessionType) -> None:
    """
    Click command helper which populates Tatoeba table in the database.

    Args:
      session (Session): SQLAlchemy Session object
    """

    click.echo("Populating Tatoeba Table ...")
    with open(TATOEBA_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    entries = []
    with click.progressbar(data,
                           label="\nPreparing Tatoeba Data -> "
                           ) as bar:
        for item in bar:
            entries.append({'id': item['id'], 'text': item['text']})

    click.echo("\nInserting Tatoeba Entries ->")
    session.bulk_insert_mappings(TatoebaSentence, entries)
    session.commit()
    click.echo("Tatoeba Table Populated.")


def populate_jlpt(session: SessionType) -> None:
    """
    Click command helper which populates JLPT tables in the database.

    Args:
      session (Session): SQLAlchemy Session object
    """

    click.echo("Populating JLPT Tables ...")
    jlpt_dir = JLPT_FOLDER
    json_files = list(jlpt_dir.glob("*.json"))
    level_pattern = re.compile(r'n(\d)')

    with click.progressbar(json_files,
                           label="Processing JLPT Files -> "
                           ) as bar:

        for json_file in bar:
            match = level_pattern.search(json_file.stem)
            if not match:
                continue
            level = int(match.group(1))

            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if "vocab" in json_file.name:
                for item in data:
                    item['level'] = level
                session.bulk_insert_mappings(JlptVocab, data)
            elif "kanji" in json_file.name:
                for item in data:
                    item['level'] = level
                    item['on_yomi'] = item.pop('on')
                    item['kun_yomi'] = item.pop('kun')
                session.bulk_insert_mappings(JlptKanji, data)
            elif "grammar" in json_file.name:
                for item in data:
                    item['level'] = level
                    item['examples'] = "\n".join(item['examples'])
                session.bulk_insert_mappings(JlptGrammar, data)

    session.commit()
    click.echo("\nJLPT Tables Populated")


@click.command('build')
@click.option('--force',
              is_flag=True,
              help="Force re-build even if the file exists."
              )
def build(force):
    """
    Downloads source files, processes, and builds the Kotobase database.
    """

    if DATABASE_PATH.exists() and not force:
        click.echo("Database file already exists. Use --force to re-build.")
        return
    elif DATABASE_PATH.exists() and force:
        try:
            DATABASE_PATH.unlink()
            click.secho("Deleted Old Database File", fg="green")

        except FileNotFoundError:
            click.secho("Database File Doesn't Exist, Remove '--force' flag.",
                        fg="red",
                        err=True
                        )
            sys.exit(1)
        except PermissionError:
            click.secho("No Permission To Delete Database File",
                        fg="red",
                        err=True
                        )
            sys.exit(1)
        except Exception as e:
            click.secho(
                f"Unexpected Error While Deleting Database File: {e}",
                fg="red",
                err=True
                )
            sys.exit(1)
    session = Session()
    try:
        start = time.perf_counter()
        click.secho("--- Step 1: Downloading raw data files ---", fg="blue")
        download_data()

        click.secho("\n--- Step 2: Processing raw data into JSON ---",
                    fg="blue")
        parse_jmdict()
        parse_jmnedict()
        parse_kanjidic()
        parse_tatoeba()

        click.secho("\n--- Step 3: Building SQLite database ---", fg="blue")
        create_database()
        populate_jmdict(session)
        populate_jmnedict(session)
        populate_kanjidic(session)
        populate_tatoeba(session)
        populate_jlpt(session)
        end = time.perf_counter()
        click.secho("\nDatabase build process complete.",
                    fg="green", bold=True)
        build_time_sec = end - start
        build_date = str(datetime.datetime.now())
        build_file_size_mb = (os.path.getsize(DATABASE_PATH) / 1024) / 1024
        build_log_txt = dedent(
            f"""BUILD_TIME={build_time_sec}
BUILD_DATE={build_date}
SIZE_MB={build_file_size_mb}
""")

        # Log Build Info
        try:
            DB_BUILD_LOG_PATH.unlink(missing_ok=True)
            DB_BUILD_LOG_PATH.touch()
            DB_BUILD_LOG_PATH.write_text(build_log_txt)
        except Exception as e:
            click.secho(f"Couldn't write log: {e}",
                        fg="yellow")
            pass

        click.secho(f"\nBuild Time: {build_time_sec} seconds")
        click.secho(f"\nBuild Date: {build_date}")
        click.secho(f"\nFile Size: {build_file_size_mb} MB")
    finally:
        # Delete Raw Files
        for p in RAW_DATA_DIR.iterdir():
            p.unlink(missing_ok=True)
        # Delete JSON Files
        JMDICT_PATH.unlink(missing_ok=True)
        JMNEDICT_PATH.unlink(missing_ok=True)
        KANJIDIC2_PATH.unlink(missing_ok=True)
        TATOEBA_PATH.unlink(missing_ok=True)
        # Close Session
        session.close()


__all__ = ["engine",
           "Session",
           "create_database",
           "populate_jmdict",
           "populate_jmnedict",
           "populate_kanjidic",
           "populate_tatoeba",
           "populate_jlpt",
           "build"
           ]


if __name__ == "__main__":
    build()
