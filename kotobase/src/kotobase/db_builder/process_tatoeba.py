import json
import csv
from kotobase.db_builder.config import (RAW_TATOEBA_PATH,
                                        TATOEBA_PATH)

def parse_tatoeba():
    """Parses jpn_sentences.tsv and saves it as a JSON file."""
    
    raw_path = RAW_TATOEBA_PATH
    processed_path = TATOEBA_PATH
    
    processed_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Parsing {raw_path}...")

    sentences = []
    with open(raw_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter='	', quoting=csv.QUOTE_NONE)
        for row in reader:
            if len(row) == 3:
                sentences.append({
                    "id": int(row[0]),
                    "lang": row[1],
                    "text": row[2]
                })

    print(f"Writing {len(sentences)} sentences to {processed_path}...")
    with open(processed_path, 'w', encoding='utf-8') as f:
        json.dump(sentences, f, ensure_ascii=False)

    print("Successfully processed Tatoeba sentences.")

if __name__ == "__main__":
    parse_tatoeba()
