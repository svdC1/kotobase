import json
from pathlib import Path
from lxml import etree
from kotobase.db_builder.config import (RAW_JMNEDICT_PATH, JMNEDICT_PATH)

def parse_jmnedict():
    """Parses JMnedict.xml and saves it as a JSON file."""
    
    raw_path = RAW_JMNEDICT_PATH
    processed_path = JMNEDICT_PATH
    
    processed_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Parsing {raw_path}...")

    entries = []
    # Use iterparse for memory-efficient parsing of the large XML file
    for _, element in etree.iterparse(raw_path, tag='entry'):
        entry = {
            "id": int(element.findtext('ent_seq')),
            "kanji": [],
            "kana": [],
            "translations": [],
        }

        # Extract kanji elements
        for k_ele in element.findall('k_ele'):
            entry["kanji"].append({"text": k_ele.findtext('keb')})

        # Extract kana elements
        for r_ele in element.findall('r_ele'):
            entry["kana"].append({"text": r_ele.findtext('reb')})
            
        # Extract translation elements
        for trans in element.findall('trans'):
            entry["translations"].append({
                "type": [t.text for t in trans.findall('name_type')],
                "translation": [t.text for t in trans.findall('trans_det')],
            })
            
        entries.append(entry)
        # Free up memory
        element.clear()
        while element.getprevious() is not None:
            del element.getparent()[0]

    print(f"Writing {len(entries)} entries to {processed_path}...")
    with open(processed_path, 'w', encoding='utf-8') as f:
        json.dump(entries, f, ensure_ascii=False)

    print("Successfully processed JMnedict.")

if __name__ == "__main__":
    parse_jmnedict()
