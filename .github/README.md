# Kotobase

[![PyPI](https://img.shields.io/pypi/v/kotobase?style=flat&logo=pypi&logoColor=white)](https://pypi.org/project/kotobase/)
[![Python](https://img.shields.io/pypi/pyversions/kotobase?style=flat&logo=python&logoColor=white)](https://pypi.org/project/kotobase/)
[![License](https://img.shields.io/badge/license-MIT-green?style=flat)](LICENSE)
[![Docs](https://img.shields.io/badge/docs-lightgrey?style=flat&logo=materialformkdocs&logoColor=black&logoSize=auto)](https://svdc1.github.io/kotobase)
[![Database Build](https://img.shields.io/github/actions/workflow/status/svdC1/kotobase/build_db.yaml?style=flat&logo=githubactions&logoColor=white&label=database-build)](https://github.com/svdC1/kotobase/actions/workflows/build_db.yaml)


A Comprehensive Japanese Language Database

`Kotobase` is a `python` package that aggregates several **openly licensed** Japanese Language data sources into one `SQLite` database and exposes simple programmatic access to it

## Quickstart

### Install

```bash
pip install kotobase
```

### Get The Database File
```bash
# Get The Latest Release From GitHub
kotobase db pull

# Download Sources & Build Locally
kotobase db build
```

### Access Data

#### CLI
```bash
# Runs Comprehensive Lookup Across All Sources
kotobase lookup all 日本語
```

#### Python
```py
from kotobase import Kotobase

kb = Kotobase()

result = kb("日本語")
```

## Features

<table>
  <tr>
    <td><b>Comprehensive Lookups</b></td>
    <td>One <code>lookup all</code> Query Aggregates Data From All Souces</td>
  </tr>
  <tr>
    <td><b>Organized Data</b></td>
    <td>Every Source Is Fully Extracted Into A Normalized <code>SQLite</code> Schema & Exposed As Typed, Serializable <code>DTOs</code></td>
  </tr>
    <tr>
    <td><b>Example Sentences</b></td>
    <td>Search <code>Tatoeba</code> Example Sentences + Their English Translation By Text </td>
  </tr>
    <tr>
    <td><b>Wildcard Search</b></td>
    <td>Match Written / Reading Forms With <code>*</code> & <code>%</code> Wildcard Patterns</td>
  </tr>
    <tr>
    <td><b>CLI</b></td>
    <td>A <code><a href=https://typer.tiangolo.com/ >Typer</a></code> + <code><a href=https://rich.readthedocs.io/en/latest/introduction.html >Rich</a></code> CLI With Readable, Panelled Output & <code>--json</code> For Scripting</td>
  </tr>
    <tr>
    <td><b>Self-Contained</b></td>
    <td>A Single <code>SQLite</code> <i>(~400MB)</i> File + Optional Audio Pack <i>(~150MB)</i>  With No Server / Network Access Needed At Query Time</td>
  </tr>
    <tr>
    <td><b>Easy Database Management</b></td>
    <td>Pull <code><a href=https://github.com/svdC1/kotobase/blob/main/.github/workflows/build_db.yaml >Pre-Built</a></code> Databases From GitHub Releases Or Build It Locally + Manage The Cache From The <code>CLI</code></td>
  </tr>
</table>

## Help

<table>
    <tr>
        <td><b><a href="https://svdc1.github.io/kotobase">Documentation</a></b></td>
        <td>Full API + CLI Reference</td>
    </tr>
        <tr>
        <td><b><a href="https://svdc1.github.io/kotobase/examples">Examples</a></b></td>
        <td>Curated Usage Examples</td>
    </tr>
    <tr>
        <td><b><a href="https://svdc1.github.io/kotobase/project/changelog">Changelog</a></b></td>
        <td>Changes Between Versions</td>
    </tr>
</table>

## Data Sources & Licenses

Every source is **openly licensed**

The compiled database is a derived work of
the sources below, and each row keeps its source and license where appropariate

See the [`Third-Party Notices`](https://svdc1.github.io/kotobase/project/notice) for the
full attribution text

<table>
  <tr>
    <td><b>Source</b></td>
    <td><b>Provides</b></td>
    <td><b>License</b></td>
  <tr>
    <td>
      <b>
        <a href=https://www.edrdg.org/jmdict/j_jmdict.html>
          <code>JMdict</code>
        </a>
      </b>
    </td>
    <td>
      Dictionary Entries &rarr; Written + Reading Forms / Senses, Glosses, Part-Of-Speech / Register / Field / Dialect Tags, Priorities
    </td>
    <td>
      CC BY-SA 4.0
    </td>
  </tr>
    <tr>
    <td>
      <b>
        <a href=https://www.edrdg.org/enamdict/enamdict_doc.html>
          <code>JMNedict</code>
        </a>
      </b>
    </td>
    <td>
      Proper Names &rarr; People / Places / Organisations + Their Types
    </td>
    <td>
      CC BY-SA 4.0
    </td>
  </tr>
  <tr>
    <td>
      <b>
        <a href=https://www.edrdg.org/wiki/index.php/KANJIDIC_Project>
          <code>KanjiDic2</code>
        </a>
      </b>
    </td>
    <td>
      Kanji Profiles &rarr; Readings / Meanings / Stroke Counts / Grades / Frequencies / SKIP / Dictionary References
    </td>
    <td>
      CC BY-SA 4.0
    </td>
  </tr>
  <tr>
    <td>
      <b>
        <a href=https://www.edrdg.org/wiki/index.php/KANJIDIC_Project>
          <code>KRADFILE / RADKFILE</code>
        </a>
      </b>
    </td>
    <td>
      Kanji To Radical Decomposition For Radical Search
    </td>
    <td>
      CC BY-SA 4.0
    </td>
  </tr>
  <tr>
    <td>
      <b>
        <a href=https://github.com/Doublevil/JmdictFurigana>
          <code>JmdictFurigana</code>
        </a>
      </b>
    </td>
    <td>
      Per-Form Furigana Segmentation
    </td>
    <td>
      CC BY-SA 4.0
    </td>
  </tr>
  <tr>
    <td>
      <b>
        <a href=https://kanjivg.tagaini.net/ >
          <code>KanjiVG</code>
        </a>
      </b>
    </td>
    <td>
      Stroke-Order SVG Paths
    </td>
    <td>
      CC BY-SA 3.0
    </td>
  </tr>
  <tr>
    <td>
      <b>
        <a href=https://tatoeba.org/ >
          <code>Tatoeba</code>
        </a>
      </b>
    </td>
    <td>
      Example Sentences With Japanese To English Translations
    </td>
    <td>
      CC BY 2.0 FR
    </td>
  </tr>
  <tr>
    <td>
      <b>
        <a href=http://www.tanos.co.uk/jlpt/ >
          <code>Tanos JLPT</code>
        </a>
      </b>
    </td>
    <td>
      JLPT Vocabulary / Kanji / Grammar Study Lists
    </td>
    <td>
      CC BY 4.0
    </td>
  </tr>
  <tr>
    <td>
      <b>
        <a href=https://kanjialive.com/ >
          <code>Kanji Alive</code>
        </a>
      </b>
    </td>
    <td>
      Word Pronunciation Audio (Optional Download)
    </td>
    <td>
      CC BY 4.0
    </td>
  </tr>
</table>

---

## Contributing

- All contributions are welcome

- See [`CONTRIBUTING`](https://svdc1.github.io/kotobase/project/contributing) for local setup, commands, and PR conventions
