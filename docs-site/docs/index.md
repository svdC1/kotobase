# Kotobase
## ![PyPI - Version](https://img.shields.io/pypi/v/kotobase?pypiBaseUrl=https%3A%2F%2Fpypi.org&style=for-the-badge&logoSize=auto) ![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/svdC1/kotobase/build_upload_db.yaml?branch=main&style=for-the-badge&label=Database%20Build)

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

-   Install the package

```bash
pip install kotobase
```

> This will install the `kotobase` package and its dependencies, and it will also make the `kotobase` command-line tool available in your shell.

-   Pull the Database from Drive or Build it locally by running of the commands below in the environment you installed kotobase

```bash
# Pull from Drive
kotobase pull-db
# Build locally
kotobase build
```

> The database will be downloaded or built internally in the package at `kotobase/src/db/kotobase.db` and will be available for use.
