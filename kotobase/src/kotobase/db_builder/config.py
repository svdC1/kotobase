from pathlib import Path

file_dir = Path(__file__).resolve().parent
pkg_root = file_dir.parent
db_module = pkg_root / "db"
# EDRDG FTP URLs for dictionary files
JMDICT_URL = "http://ftp.edrdg.org/pub/Nihongo/JMdict_e.gz"
JMNEDICT_URL = "http://ftp.edrdg.org/pub/Nihongo/JMnedict.xml.gz"
KANJIDIC2_URL = "http://www.edrdg.org/kanjidic/kanjidic2.xml.gz"

# Tatoeba URL for Japanese sentences
TATOEBA_URL = ("https://downloads.tatoeba.org/exports/per_language/jpn/"
               "jpn_sentences.tsv.bz2")

# Data directory to store raw and processed data
DATA_DIR = file_dir / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
DATABASE_PATH = db_module / "kotobase.db"
JMDICT_PATH = PROCESSED_DATA_DIR / "jmdict.json"
JMNEDICT_PATH = PROCESSED_DATA_DIR / "jmnedict.json"
KANJIDIC2_PATH = PROCESSED_DATA_DIR / "kanjidic.json"
TATOEBA_PATH = PROCESSED_DATA_DIR / "tatoeba.json"
JLPT_FOLDER = PROCESSED_DATA_DIR / "jlpt"
JLPT_PATHS = {
    "grammar": {
        "n1": JLPT_FOLDER / "grammar_n1.json",
        "n2": JLPT_FOLDER / "grammar_n2.json",
        "n3": JLPT_FOLDER / "grammar_n3.json",
        "n4": JLPT_FOLDER / "grammar_n4.json",
        "n5": JLPT_FOLDER / "grammar_n5.json"
            },
    "kanji": {
        "n1": JLPT_FOLDER / "kanji_n1.json",
        "n2": JLPT_FOLDER / "kanji_n2.json",
        "n3": JLPT_FOLDER / "kanji_n3.json",
        "n4": JLPT_FOLDER / "kanji_n4.json",
        "n5": JLPT_FOLDER / "kanji_n5.json"
    },
    "vocab": {
        "n1": JLPT_FOLDER / "vocab_n1.json",
        "n2": JLPT_FOLDER / "vocab_n2.json",
        "n3": JLPT_FOLDER / "vocab_n3.json",
        "n4": JLPT_FOLDER / "vocab_n4.json",
        "n5": JLPT_FOLDER / "vocab_n5.json"
    }
    }

# Raw Data Paths
RAW_JMDICT_PATH = RAW_DATA_DIR / "JMdict_e.xml"
RAW_JMNEDICT_PATH = RAW_DATA_DIR / "JMnedict.xml"
RAW_KANJIDIC2_PATH = RAW_DATA_DIR / "kanjidic2.xml"
RAW_TATOEBA_PATH = RAW_DATA_DIR / "jpn_sentences.tsv"

__all__ = ["file_dir",
           "pkg_root",
           "db_module",
           "JMDICT_URL",
           "JMNEDICT_URL",
           "KANJIDIC2_URL",
           "DATA_DIR",
           "RAW_DATA_DIR",
           "PROCESSED_DATA_DIR",
           "DATABASE_PATH",
           "JMDICT_PATH",
           "JMNEDICT_PATH",
           "KANJIDIC2_PATH",
           "TATOEBA_PATH",
           "JLPT_FOLDER",
           "JLPT_PATHS",
           "RAW_JMDICT_PATH",
           "RAW_JMNEDICT_PATH",
           "RAW_KANJIDIC2_PATH",
           "RAW_TATOEBA_PATH"
           ]
