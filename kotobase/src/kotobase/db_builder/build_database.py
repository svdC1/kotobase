import json
import re
import os
import click
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
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
                                        KANJIDIC2_PATH)
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
                                jmdict_kanji_assoc,
                                jmdict_kana_assoc
                                )

# --- Database Setup ---
engine = create_engine(f'sqlite:///{DATABASE_PATH}')
Session = sessionmaker(bind=engine)


def create_database():
    """Creates the database and all tables."""
    if not DATABASE_PATH.exists():
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
    click.echo("Database created successfully.")


def populate_jmdict(session):
    click.echo("Populating JMDict tables...")
    with open(JMDICT_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    entries, kanji_entries, kana_entries, sense_entries = [], [], [], []
    kanji_assoc, kana_assoc = [], []
    kanji_cache, kana_cache = {}, {}

    with click.progressbar(data, label="  -> Preparing JMDict data...") as bar:
        for item in bar:
            entries.append({'id': item['id']})
            for k in item.get('kanji', []):
                if k['text'] not in kanji_cache:
                    kanji_id = len(kanji_cache) + 1
                    kanji_cache[k['text']] = kanji_id
                    kanji_entries.append({'id': kanji_id, 'text': k['text']})
                kanji_assoc.append({'jmdict_id': item['id'],
                                    'kanji_id': kanji_cache[k['text']]})
            for r in item.get('kana', []):
                if r['text'] not in kana_cache:
                    kana_id = len(kana_cache) + 1
                    kana_cache[r['text']] = kana_id
                    kana_entries.append({'id': kana_id,
                                         'text': r['text']})
                kana_assoc.append({'jmdict_id': item['id'],
                                   'kana_id': kana_cache[r['text']]})
            for s in item.get('senses', []):
                sense_entries.append({
                    'entry_id': item['id'],
                    'order': s.get('order'),
                    'pos': ", ".join(s.get('pos', [])),
                    'gloss': ", ".join(s.get('gloss', []))
                })

    click.echo("\n-> Inserting JMDict data...")
    session.bulk_insert_mappings(JMDictEntry, entries)
    session.bulk_insert_mappings(JMDictKanji, kanji_entries)
    session.bulk_insert_mappings(JMDictKana, kana_entries)
    session.bulk_insert_mappings(JMDictSense, sense_entries)
    if kanji_assoc:
        session.execute(jmdict_kanji_assoc.insert(), kanji_assoc)
    if kana_assoc:
        session.execute(jmdict_kana_assoc.insert(), kana_assoc)
    session.commit()
    click.echo("JMDict tables populated.")


def populate_jmnedict(session):
    click.echo("Populating JMnedict table...")
    with open(JMNEDICT_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    entries = []
    with click.progressbar(data,
                           label="  -> Preparing JMnedict data...") as bar:
        for item in bar:
            types = [
                t for sublist in item['translations'] for t in sublist['type']]
            translations = [
                t for sublist in item[
                    'translations'] for t in sublist['translation']]
            entries.append({
                'id': item['id'],
                'kanji': ", ".join([k['text'] for k in item['kanji']]),
                'kana': ", ".join([k['text'] for k in item['kana']]),
                'translation_type': ", ".join(types),
                'translation': ", ".join(translations)
            })

    click.echo("\n-> Inserting JMnedict entries...")
    session.bulk_insert_mappings(JMnedictEntry, entries)
    session.commit()
    click.echo("JMnedict table populated.")


def populate_kanjidic(session):
    click.echo("Populating Kanjidic table...")
    with open(KANJIDIC2_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    entries = []
    with click.progressbar(data,
                           label="  -> Preparing Kanjidic data...") as bar:
        for item in bar:
            on_readings = [
                r['value'] for r in item['reading_meaning'][
                    'readings'] if r['type'] == 'ja_on']
            kun_readings = [
                r['value'] for r in item['reading_meaning'][
                    'readings'] if r['type'] == 'ja_kun']
            meanings = [
                m['value'] for m in item['reading_meaning'][
                    'meanings'] if m['lang'] == 'en']
            entries.append({
                'literal': item['literal'],
                'grade': item.get('grade'),
                'stroke_count': item['stroke_count'][0] if item[
                    'stroke_count'] else None,
                'jlpt': item.get('jlpt'),
                'on_readings': ", ".join(on_readings),
                'kun_readings': ", ".join(kun_readings),
                'meanings': ", ".join(meanings)
            })

    click.echo("\n-> Inserting Kanjidic entries...")
    session.bulk_insert_mappings(Kanjidic, entries)
    session.commit()
    click.echo("Kanjidic table populated.")


def populate_tatoeba(session):
    click.echo("Populating Tatoeba table...")
    with open(TATOEBA_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    entries = []
    with click.progressbar(data,
                           label="  -> Preparing Tatoeba data...") as bar:
        for item in bar:
            entries.append({'id': item['id'], 'text': item['text']})

    click.echo("\n-> Inserting Tatoeba entries...")
    session.bulk_insert_mappings(TatoebaSentence, entries)
    session.commit()
    click.echo("Tatoeba table populated.")


def populate_jlpt(session):
    click.echo("Populating JLPT tables...")
    jlpt_dir = JLPT_FOLDER
    json_files = list(jlpt_dir.glob("*.json"))
    level_pattern = re.compile(r'n(\d)')

    with click.progressbar(json_files,
                           label="  -> Processing JLPT files...") as bar:
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
    click.echo("\nJLPT tables populated.")


@click.command('build')
@click.option('--force',
              is_flag=True,
              help="Force re-build even if the file exists."
              )
def build(force):
    """Downloads source files, processes, and builds the Kotobase database."""

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
