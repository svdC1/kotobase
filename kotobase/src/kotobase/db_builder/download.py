from pathlib import Path
import requests
import gzip
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
    raw_data_path = file_dir / RAW_DATA_DIR
    output_path = raw_data_path / output_filename

    print(f"Downloading {url}...")
    response = requests.get(url, stream=True)
    response.raise_for_status()

    with open(output_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    print(f"Extracting {output_path}...")
    if url.endswith(".gz"):
        uncompressed_path = output_path.with_suffix('')
        with gzip.open(output_path, "rb") as f_in:
            with open(uncompressed_path, "wb") as f_out:
                f_out.write(f_in.read())
        output_path.unlink()
    elif url.endswith(".bz2"):
        uncompressed_path = output_path.with_suffix('')
        with bz2.open(output_path, "rb") as f_in:
            with open(uncompressed_path, "wb") as f_out:
                f_out.write(f_in.read())
        output_path.unlink()
        print(f"Successfully downloaded and extracted {output_filename}")


def main():
    """Main function to download all data sources."""
    (file_dir / RAW_DATA_DIR).mkdir(parents=True, exist_ok=True)
    download_and_extract(JMDICT_URL, "JMdict_e.xml.gz")
    download_and_extract(JMNEDICT_URL, "JMnedict.xml.gz")
    download_and_extract(KANJIDIC2_URL, "kanjidic2.xml.gz")
    download_and_extract(TATOEBA_URL, "jpn_sentences.tsv.bz2")


if __name__ == "__main__":
    main()
