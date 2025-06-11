# Kotobase

Kotobase is a Python package that provides a comprehensive, pre-built SQLite database of Japanese language resources, along with a simple API for querying the data. It's designed to be an easy-to-use, up-to-date replacement for the now-outdated Jamdict library.

## Features

- **Comprehensive Data:** Includes JMDict, JMnedict, Kanjidic2, Tatoeba Japanese sentences, and JLPT vocabulary, kanji, and grammar lists.
- **Pre-built Database:** The package includes a ready-to-use SQLite database, so there's no need for a complex setup process.
- **Simple API:** A straightforward, SQLAlchemy-based API for querying the database.
- **Regular Updates:** The database is rebuilt weekly with the latest data from the source dictionaries.

## Installation

You can install Kotobase directly from this repository using pip:

```bash
pip install .
```

## Quick Start

Here's a simple example of how to use Kotobase to perform a comprehensive lookup of a word:

```python
from kotobase import Kotobase

with Kotobase() as kb:
    # Perform a comprehensive lookup of the word "猫"
    word_info = kb.lookup_word("猫")

    # Print the JMDict entries
    for entry in word_info["jmdict_entries"]:
        print(f"JMDict Entry: {entry.kanji[0].text if entry.kanji else entry.kana[0].text}")
        for i, sense in enumerate(entry.senses):
            print(f"  Sense {i+1}: {sense.gloss}")

    # Print Kanjidic information
    for kanji in word_info["kanjidic_entries"]:
        if kanji:
            print(f"Kanji: {kanji.literal} (JLPT N{kanji.jlpt})")
            print(f"  Meaning: {kanji.meanings}")

    # Print Tatoeba example sentences
    print("Tatoeba Examples:")
    for sentence in word_info["tatoeba_sentences"]:
        print(f"  - {sentence.text}")
```

## API Overview

The `kotobase.Kotobase` class provides a simple and convenient way to query the database.

### Comprehensive Lookup

- `lookup_word(word)`: Performs a comprehensive lookup of a word, returning a dictionary with JMDict entries, Kanjidic entries, Tatoeba sentences, and JLPT information.

### Direct Access Methods

- `find_word(query)`: Finds a word in JMDict.
- `find_kanji(literal)`: Finds a kanji in Kanjidic.
- `get_jmdict_entries()`: Returns all entries from JMDict.
- `get_jmnedict_entries()`: Returns all entries from JMnedict.
- `get_kanjidic_entries()`: Returns all entries from Kanjidic.
- `get_tatoeba_sentences()`: Returns all sentences from Tatoeba.
- `get_jlpt_vocab(level)`: Gets the JLPT vocabulary list for a given level.
- `get_jlpt_kanji(level)`: Gets the JLPT kanji list for a given level.
- `get_jlpt_grammar(level)`: Gets the JLPT grammar list for a given level.

All data is returned as SQLAlchemy model objects, which can be easily used in your Python code.
