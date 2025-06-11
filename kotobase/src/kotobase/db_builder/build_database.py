import json
import sys
import re
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from kotobase.db_builder.config import (DATABASE_PATH,
                                        JMDICT_PATH,
                                        JMNEDICT_PATH,
                                        TATOEBA_PATH,
                                        JLPT_FOLDER,
                                        KANJIDIC2_PATH)
from kotobase.db.models import (
    Base, JMDictEntry, JMDictKanji, JMDictKana, JMDictSense,
    JMnedictEntry, Kanjidic, TatoebaSentence,
    JlptVocab, JlptKanji, JlptGrammar
)

file_dir = Path(__file__).resolve().parent


# Database setup
DATABASE_FILE = DATABASE_PATH
engine = create_engine(f'sqlite:///{DATABASE_FILE}')
Session = sessionmaker(bind=engine)
session = Session()

def _log_progress(count, total, message):
    """Logs progress to the console."""
    percent = int((count / total) * 100)
    sys.stdout.write(f"\n{message} {count}/{total} ({percent}%)")
    sys.stdout.flush()

def create_database():
    """Creates the database and all tables."""
    # We need to make sure the db file exists for the models to be created
    if not DATABASE_FILE.exists():
        DATABASE_FILE.touch()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    print("Database created successfully.")

def populate_jmdict():
    print("Populating JMDict tables...")
    with open(JMDICT_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    total = len(data)
    kanji_cache = {}
    kana_cache = {}

    for i, item in enumerate(data):
        entry = JMDictEntry(id=item['id'])
        
        for k in item['kanji']:
            if k['text'] not in kanji_cache:
                kanji = JMDictKanji(text=k['text'])
                session.add(kanji)
                kanji_cache[k['text']] = kanji
            else:
                kanji = kanji_cache[k['text']]
            entry.kanji.append(kanji)
            
        for r in item['kana']:
            if r['text'] not in kana_cache:
                kana = JMDictKana(text=r['text'])
                session.add(kana)
                kana_cache[r['text']] = kana
            else:
                kana = kana_cache[r['text']]
            entry.kana.append(kana)
            
        sorted_senses = sorted(item['senses'], key=lambda s: s['order'])
        for s in sorted_senses:
            sense = JMDictSense(
                order=s['order'],
                pos=", ".join(s['pos']), 
                gloss=", ".join(s['gloss'])
            )
            entry.senses.append(sense)
        
        session.add(entry)
        
        if (i + 1) % 10000 == 0:
            _log_progress(i + 1, total, "  -> Processing JMDict entries...")
            session.commit()

    session.commit()
    _log_progress(total, total, "  -> Processing JMDict entries...")
    print("\nJMDict tables populated.")

def populate_jmnedict():
    print("Populating JMnedict table...")
    with open(JMNEDICT_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    total = len(data)
    for i, item in enumerate(data):
        types = [t for sublist in item['translations'] for t in sublist['type']]
        translations = [t for sublist in item['translations'] for t in sublist['translation']]
        
        entry = JMnedictEntry(
            id=item['id'],
            kanji=", ".join([k['text'] for k in item['kanji']]),
            kana=", ".join([k['text'] for k in item['kana']]),
            translation_type=", ".join(types),
            translation=", ".join(translations)
        )
        session.add(entry)

        if (i + 1) % 10000 == 0:
            _log_progress(i + 1, total, "  -> Processing JMnedict entries...")
            session.commit()

    session.commit()
    _log_progress(total, total, "  -> Processing JMnedict entries...")
    print("\nJMnedict table populated.")

def populate_kanjidic():
    print("Populating Kanjidic table...")
    with open(KANJIDIC2_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    total = len(data)
    for i, item in enumerate(data):
        on_readings = [r['value'] for r in item['reading_meaning']['readings'] if r['type'] == 'ja_on']
        kun_readings = [r['value'] for r in item['reading_meaning']['readings'] if r['type'] == 'ja_kun']
        meanings = [m['value'] for m in item['reading_meaning']['meanings'] if m['lang'] == 'en']
        
        entry = Kanjidic(
            literal=item['literal'],
            grade=item.get('grade'),
            stroke_count=item['stroke_count'][0] if item['stroke_count'] else None,
            jlpt=item.get('jlpt'),
            on_readings=", ".join(on_readings),
            kun_readings=", ".join(kun_readings),
            meanings=", ".join(meanings)
        )
        session.add(entry)
        if (i + 1) % 1000 == 0:
            _log_progress(i + 1, total, "  -> Processing Kanjidic entries...")
            session.commit()

    session.commit()
    _log_progress(total, total, "  -> Processing Kanjidic entries...")
    print("\nKanjidic table populated.")

def populate_tatoeba():
    print("Populating Tatoeba table...")
    with open(TATOEBA_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    total = len(data)
    for i, item in enumerate(data):
        entry = TatoebaSentence(id=item['id'], text=item['text'])
        session.add(entry)
        if (i + 1) % 10000 == 0:
            _log_progress(i + 1, total, "  -> Processing Tatoeba sentences...")
            session.commit()
    
    session.commit()
    _log_progress(total, total, "  -> Processing Tatoeba sentences...")
    print("\nTatoeba table populated.")

def populate_jlpt():
    print("Populating JLPT tables...")
    jlpt_dir = JLPT_FOLDER
    json_files = list(jlpt_dir.glob("*.json"))
    total = len(json_files)
    level_pattern = re.compile(r'n(\d)')

    for i, json_file in enumerate(json_files):
        print(f"\n-> Processing file: {json_file.name} ({i+1}/{total})")
        match = level_pattern.search(json_file.stem)
        if not match:
            continue
        level = int(match.group(1))
        
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        if "vocab" in json_file.name:
            for item in data:
                session.add(JlptVocab(level=level, **item))
        elif "kanji" in json_file.name:
            for item in data:
                item_fixed = {'on_yomi': item.pop('on'), 'kun_yomi': item.pop('kun'), **item}
                session.add(JlptKanji(level=level, **item_fixed))
        elif "grammar" in json_file.name:
            for item in data:
                item['examples'] = "\n".join(item['examples'])
                session.add(JlptGrammar(level=level, **item))
    
    session.commit()
    print("\nJLPT tables populated.")

def main():
    """Main function to build the database."""
    create_database()
    populate_jmdict()
    populate_jmnedict()
    populate_kanjidic()
    populate_tatoeba()
    populate_jlpt()
    print("\nDatabase build process complete.")

if __name__ == "__main__":
    main()
