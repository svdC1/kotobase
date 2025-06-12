import json
import csv
import click
from kotobase.db_builder.config import (RAW_TATOEBA_PATH,
                                        TATOEBA_PATH)


def parse_tatoeba():
    """Parses jpn_sentences.tsv and saves it as a JSON file."""

    raw_path = RAW_TATOEBA_PATH
    processed_path = TATOEBA_PATH

    processed_path.parent.mkdir(parents=True, exist_ok=True)

    click.echo(f"Parsing {raw_path.name}...")

    sentences = []
    with open(raw_path, 'r', encoding='utf-8') as f:
        # Get total number of lines for progress bar
        total_lines = sum(1 for line in f)
        f.seek(0)

        reader = csv.reader(f, delimiter='	', quoting=csv.QUOTE_NONE)
        with click.progressbar(reader, length=total_lines,
                               label="  -> Processing sentences...") as bar:
            for row in bar:
                if len(row) == 3:
                    sentences.append({
                        "id": int(row[0]),
                        "lang": row[1],
                        "text": row[2]
                    })

    click.echo(f"\nWriting {len(sentences)} \
        sentences to {processed_path.name}...")
    with open(processed_path, 'w', encoding='utf-8') as f:
        json.dump(sentences, f, ensure_ascii=False)

    click.secho("Successfully processed Tatoeba sentences.", fg="green")


__all__ = ["parse_tatoeba"]


if __name__ == "__main__":
    parse_tatoeba()
