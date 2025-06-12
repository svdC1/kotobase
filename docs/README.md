# Kotobase

**Kotobase is a Japanese language Python package which provides simple programmatic access to various data sources via a pre-built database which is updated weekly via a GitHub action.**

## Data Sources

Kotobase uses data from these sources to build its Database.

-   [`JMDict`](http://www.edrdg.org/jmdict/j_jmdict.html) : Japanese-Multilingual Dictionary.

-   [`JMnedict`](http://www.edrdg.org/enamdict/enamdict_doc.html) : A dictionary of Japanese proper names.

-   [`KanjiDic2`](http://www.edrdg.org/kanjidic/kanjd2index_legacy.html) : A comprehensive kanji dictionary.

-   [`Tatoeba`](https://tatoeba.org/en/) : A large database of example sentences.

-   [`JLPT Lists`](http://www.tanos.co.uk/) : Curated list of Grammar, Vocabulary and Kanji separated by Japanese Language Proficiency Test levels, made available on Jonathan Weller's website.

### Licenses

> The licenses of these data sources and the NOTICE is available at `docs/licenses` in this repository.

## Features

-   **Comprehensive Lookups** &rarr; Search for words (kanji, kana, or romaji), kanji, and proper names.

-   **Organized Data** &rarr; Get detailed information including readings, senses, parts of speech, kanji stroke counts, meanings, and JLPT levels formatted into Python Data Objects.

-   **Example Sentences** &rarr; Find example sentences from Tatoeba that contain the searched query.

-   **Wildcard Search** &rarr; Use `*` or `%` for wildcard searches.

-   **Command-Line Interface** &rarr; User-friendly CLI for quick lookups from the terminal.

-   **Self-Contained** &rarr; All data is stored in a local SQLite database, so it's fast and works offline.

-   **Easy Database Management** &rarr; Includes commands to automatically download the latest pre-built database from the public Drive or download source files and build the database locally.

## Installation

```bash
pip install kotobase
```

This will install the `kotobase` package and its dependencies, and it will also make the `kotobase` command-line tool available in your shell.

## Usage

Kotobase can be used as a command-line tool or as a Python library.

### Command-Line Interface

The `kotobase` command provides several subcommands for different types of lookups.

#### General Lookup

The `lookup` command is the most comprehensive way to search for a word.

```bash
kotobase lookup 日本語
```

This will show you dictionary entries, kanji information, JLPT levels, and example sentences for the word "日本語".

**Options:**

-   `-n`, `--names`: Include proper names from JMnedict in the search.
-   `-w`, `--wildcard`: Treat `*` or `%` as wildcards in the search term.
-   `-s`, `--sentences`: Specify the number of example sentences to show.
-   `--json-out`: Output the full results as a JSON object.

#### Kanji Lookup

To get information about a specific kanji character:

```bash
kotobase kanji 語
```

This will display the kanji's grade, stroke count, meanings, on'yomi, and kun'yomi readings, and JLPT level.

#### JLPT Lookup

To check the JLPT level for a word or kanji:

```bash
kotobase jlpt 勉強
```

### Python API

You can also use Kotobase in your own Python code.

```python
from kotobase import Kotobase

kb = Kotobase()

# Comprehensive lookup
result = kb.lookup("日本語")
print(result.to_json(indent=2, ensure_ascii=False))

# Get info for a single kanji
kanji_info = kb.kanji("語")
print(kanji_info)

# Get example sentences
sentences = kb.sentences("勉強")
for sentence in sentences:
    print(sentence.text)
```

## Database

Kotobase relies on a local SQLite database.

You can also build it from the source files yourself.

The following commands are available for managing the database:

-   `kotobase pull-db`: Downloads the pre-built SQLite database from a public [`Google Drive Folder`](https://drive.google.com/drive/u/0/folders/14wbgMyp0TubFyFaUy0W_CnK9_z7fo_Fv). This file is overwritten every week with a rebuilt database from updated sources. The rebuilding and overwriting is managed by a GitHub action in this repository.

-   `kotobase build`: Builds the SQLite database from the raw source files. This will download the latest version of the source files (_Except Tanos JLPT lists which are shipped with the package itself._) and build the database locally.
