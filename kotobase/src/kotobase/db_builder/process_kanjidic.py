import json
import click
from lxml import etree
from kotobase.db_builder.config import (RAW_KANJIDIC2_PATH,
                                        KANJIDIC2_PATH)


def parse_kanjidic():
    """Parses kanjidic2.xml and saves it as a JSON file."""

    raw_path = RAW_KANJIDIC2_PATH
    processed_path = KANJIDIC2_PATH

    processed_path.parent.mkdir(parents=True, exist_ok=True)

    click.echo(f"Parsing {raw_path.name}...")

    characters = []
    # Use iterparse for memory-efficient parsing
    with click.progressbar(etree.iterparse(raw_path, tag='character'),
                           label="  -> Processing characters...",
                           item_show_func=lambda x: "") as bar:
        for _, element in bar:
            character = {
                "literal": element.findtext('literal'),
                "codepoint": [
                    {"type": cp.get('cp_type'), "value": cp.text}
                    for cp in element.findall('codepoint/cp_value')
                ],
                "radical": [
                    {"type": rad.get('rad_type'), "value": rad.text}
                    for rad in element.findall('radical/rad_value')
                ],
                "grade": element.findtext('misc/grade'),
                "stroke_count": [
                    sc.text for sc in element.findall('misc/stroke_count')],
                "variants": [
                    {"type": var.get('var_type'), "value": var.text}
                    for var in element.findall('misc/variant')
                ],
                "freq": element.findtext('misc/freq'),
                "jlpt": element.findtext('misc/jlpt'),
                "dic_number": [
                    {"type": dr.get('dr_type'),
                     "m_vol": dr.get('m_vol'),
                     "m_page": dr.get('m_page'),
                     "value": dr.text}
                    for dr in element.findall('dic_number/dic_ref')
                ],
                "query_code": [
                    {"type": qc.get('qc_type'),
                     "skip_misclass": qc.get('skip_misclass'),
                     "value": qc.text}
                    for qc in element.findall('query_code/q_code')
                ],
                "reading_meaning": {
                    "readings": [
                        {"type": r.get('r_type'),
                         "on_type": r.get('on_type'),
                         "r_status": r.get('r_status'),
                         "value": r.text}
                        for r in element.findall(
                            'reading_meaning/rmgroup/reading')
                    ],
                    "meanings": [
                        {"lang": m.get('m_lang', 'en'),
                         "value": m.text}
                        for m in element.findall(
                            'reading_meaning/rmgroup/meaning')
                    ]
                }
            }

            characters.append(character)
            # Free up memory
            element.clear()
            while element.getprevious() is not None:
                del element.getparent()[0]

    click.echo(f"\nWriting {len(characters)} characters\
        to {processed_path.name}...")
    with open(processed_path, 'w', encoding='utf-8') as f:
        json.dump(characters, f, ensure_ascii=False)

    click.secho("Successfully processed Kanjidic2.", fg="green")


__all__ = ["parse_kanjidic"]


if __name__ == "__main__":
    parse_kanjidic()
