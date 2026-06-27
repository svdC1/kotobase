# Kotobase

A comprehensive, openly-licensed Japanese language database.

`Kotobase` aggregates several openly-licensed Japanese language data sources
into one `SQLite` database and exposes simple programmatic and command line
access to it

## Install

```bash
pip install kotobase
```

## Get The Database

???+ abstract "Database"
    - The compiled database is a `pre-requisite` and is not bundled with the package due to its size

    - The `core` database contains all sources except for the `Kanji Alive` audio clips and is a `~400MB` `SQLite` file

    - The optional `audio` database adds `~150MB` to that size

    - There are 2 way to get both of them

    === "Pull The Pre-Built Versions"
        Both databases are rebuilt weekly with updated sources via a [`GitHub Action`](https://github.com/svdC1/kotobase/blob/main/.github/workflows/build_db.yaml) and appended as assets to the [`Latest Kotobase GitHub Release`](https://github.com/svdC1/kotobase/releases/tag/latest)
        ```bash
        kotobase db pull  # (1)!

        kotobase db pull --no-audio # (2)!
        ```

        1. Download The `Core` + `Audio` Databases
        2. Download Only The `Core` Database

    === "Build Them Locally"
        You can also easily download the most up-to-date sources and build both databases yourself via the `CLI` in `~2-3` minutes
        ```bash
        kotobase db build  # (1)!

        kotobase db build --no-audio  # (2)!
        ```

        1. Download All Sources & Build The `Core` + `Audio` Databases
        2. Download All Sources & Build Only The `Core` Database

## Use It

=== "CLI"

    ```bash
    kotobase lookup all 日本語  # (1)!

    kotobase lookup kanji 語  # (2)!
    ```

    1. Comprehensive Lookup Across Every Source
    2. A Single Kanji Profile

=== "Python"

    ```python
    from kotobase import Kotobase

    kb = Kotobase()

    result = kb("日本語")  # (1)!
    print(result.to_json())

    kanji = kb.kanji("語")
    print(kanji.meanings, kanji.onyomi, kanji.kunyomi)
    ```

    1. Alias For `kb.lookup("日本語")`

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

## More Information


<div class="grid cards" markdown>

- :material-beaker-check-outline: **[Examples](examples.md)**

    Task-Oriented Python Snippets

- :material-console: **[CLI Reference](cli.md)**

    All `kotobase` Commands

- :material-api: **[API Reference](reference/index.md)**

    Technical Documentation Of The `Kotobase` Wrapper + Data Objects

- :material-book-open-variant: **[Changelog](project/changelog.md)**

    What changed between versions

- :material-api: **[Versioning Policy](project/versioning.md)**

    What The Public API Covers

- :material-license: **[Third-Party Notices](project/notice.md)**

    Source Attribution
</div>
