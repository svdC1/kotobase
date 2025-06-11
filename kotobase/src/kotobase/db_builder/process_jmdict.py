import json
from pathlib import Path
from lxml import etree
from kotobase.db_builder.config import (RAW_JMDICT_PATH,
                                        JMDICT_PATH)


def parse_jmdict():
    """Parses JMdict_e.xml and saves it as a JSON file."""
    
    raw_path = RAW_JMDICT_PATH
    processed_path = JMDICT_PATH
    
    processed_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Parsing {raw_path}...")

    entries = []
    # Use iterparse for memory-efficient parsing of the large XML file
    for _, element in etree.iterparse(raw_path, tag='entry'):
        entry = {
            "id": int(element.findtext('ent_seq')),
            "kanji": [],
            "kana": [],
            "senses": [],
        }

        # Extract kanji elements
        for k_ele in element.findall('k_ele'):
            entry["kanji"].append({
                "text": k_ele.findtext('keb'),
                "info": [info.text for info in k_ele.findall('ke_inf')],
                "priority": [p.text for p in k_ele.findall('ke_pri')]
            })

        # Extract kana elements
        for r_ele in element.findall('r_ele'):
            entry["kana"].append({
                "text": r_ele.findtext('reb'),
                "no_kanji": r_ele.find('re_nokanji') is not None,
                "restrictions": [r.text for r in r_ele.findall('re_restr')],
                "info": [info.text for info in r_ele.findall('re_inf')],
                "priority": [p.text for p in r_ele.findall('re_pri')]
            })
            
        # Extract sense elements with order
        for i, sense in enumerate(element.findall('sense')):
            entry["senses"].append({
                "order": i,
                "applies_to_kanji": [s.text for s in sense.findall('stagk')],
                "applies_to_kana": [s.text for s in sense.findall('stagr')],
                "pos": [p.text for p in sense.findall('pos')],
                "gloss": [g.text for g in sense.findall('gloss')],
                "misc": [m.text for m in sense.findall('misc')],
                "info": [i.text for i in sense.findall('s_inf')],
            })
            
        entries.append(entry)
        # Free up memory
        element.clear()
        while element.getprevious() is not None:
            del element.getparent()[0]

    print(f"Writing {len(entries)} entries to {processed_path}...")
    with open(processed_path, 'w', encoding='utf-8') as f:
        json.dump(entries, f, ensure_ascii=False)

    print("Successfully processed JMDict.")

if __name__ == "__main__":
    parse_jmdict()
