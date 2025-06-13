from pathlib import Path
import requests
import gzip
import click
import sys
import bz2
from kotobase.db_builder.config import (
    JMDICT_URL,
    JMNEDICT_URL,
    KANJIDIC2_URL,
    TATOEBA_URL,
    RAW_DATA_DIR,
    )

file_dir = Path(__file__).resolve().parent
project_root = file_dir.parent


def download_and_extract(url: str, output_filename: str):
    """Downloads a file from a URL and extracts it if compressed."""
    try:
        output_path = RAW_DATA_DIR / output_filename
        # Delete if it already exists
        output_path.unlink(missing_ok=True)
        click.secho(f"Downloading {url}...",
                    fg="blue")
        response = requests.get(url, stream=True)
        response.raise_for_status()

        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        click.secho("  Download Successful",
                    fg="green")

        if url.endswith(".gz"):
            uncompressed_path = output_path.with_suffix('')
            # Delete if it already exists
            uncompressed_path.unlink(missing_ok=True)
            click.secho(f"  Extracting to {uncompressed_path}...",
                        fg="blue")
            with gzip.open(output_path, "rb") as f_in:
                with open(uncompressed_path, "wb") as f_out:
                    f_out.write(f_in.read())
            output_path.unlink()
            click.secho("  Done!",
                        fg="green")
        elif url.endswith(".bz2"):
            uncompressed_path = output_path.with_suffix('')
            # Delete if it already exists
            uncompressed_path.unlink(missing_ok=True)
            click.secho(f"  Extracting to {uncompressed_path}...",
                        fg="blue")
            with bz2.open(output_path, "rb") as f_in:
                with open(uncompressed_path, "wb") as f_out:
                    f_out.write(f_in.read())
            output_path.unlink()
            click.secho("  Done!",
                        fg="bright_green")
    except Exception as e:
        click.secho(f"Error while downloading {url} : {e}",
                    fg="red",
                    err=True
                    )
        sys.exit(1)


def main():
    """Main function to download all data sources."""
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    download_and_extract(JMDICT_URL, "JMdict_e.xml.gz")
    download_and_extract(JMNEDICT_URL, "JMnedict.xml.gz")
    download_and_extract(KANJIDIC2_URL, "kanjidic2.xml.gz")
    download_and_extract(TATOEBA_URL, "jpn_sentences.tsv.bz2")


if __name__ == "__main__":
    main()
