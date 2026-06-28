# CLI Reference

The `kotobase` command line is built with [`Typer`](https://typer.tiangolo.com/)
and rendered with [`Rich`](https://rich.readthedocs.io/)

It's organized into 3 `command groups` + a couple of `root commands`

Most `lookup` commands accept `-j` / `--json` to emit machine readable `JSON`
instead of the panelled output

???+ tip "View This Information In The Terminal"
    ```bash
    kotobase --help  # (1)!
    ```

    1. View The Full Command Tree

## Lookup Commands

`kotobase lookup` Commands Query The Database

!!! warning "Pre-Requisite"
    - Every `lookup` command needs the database

    - If it's missing, the command prints a hint to run `kotobase db pull` or `kotobase db build` and exits
      with a non-zero status

### `lookup all`

Runs a comprehensive lookup across every source and render one aggregated panel

```bash
kotobase lookup all QUERY [OPTIONS]
```

#### Options

| Option | Description |
| --- | --- |
| `-n / --names` | Include proper name results from JMnedict |
| `-w / --wildcard` | Treat `*` + `%` As Wildcards In The Query |
| `-sl / --sentence-limit` | Number Of Example Sentences To Show (Default `5`) |
| `-l / --labels` | Expand Tag Codes To Their Descriptions |
| `-j / --json` | Format Result As `JSON` |

#### Examples
```bash
kotobase lookup all 日本語  # (1)!
kotobase lookup all "食べ*" -w  # (2)!
kotobase lookup all 田中 -n  # (3)!
kotobase lookup all 勉強 -l  # (4)!
```

1. Dictionary Etries, Kanji, JLPT, and Sentences For The Word
2. Treat `*` + `%` As Wildcards
3. Also Include Proper Names From `JMnedict`
4. Expand Dictionary Tag Codes To Their Human Description

### `lookup kanji`

Displays the full profile of a single kanji, its readings, meanings, stroke count, grade, frequency, JLPT level, radicals, SKIP and dictionary references

```bash
kotobase lookup kanji LITERAL [OPTIONS]
```

#### Options

| Option | Description |
| --- | --- |
| `-j / --json` | Format Result As `JSON` |

#### Examples
```bash
kotobase lookup kanji 語  # (1)!
kotobase lookup kanji 語 -j  # (2)!
```

1. The Full Kanji Profile As A Panel
2. The Same Data As `JSON`

### `lookup jlpt`

Shows the JLPT vocabulary level of a word and the JLPT level of each kanji in it

```bash
kotobase lookup jlpt WORD
```

#### Examples
```bash
kotobase lookup jlpt 勉強  # (1)!
```

1. The Vocabulary Level Plus Each Kanji's Level

### `lookup kanji-find`

Searches kanji by scalar attributes, combine filters to narrow the results

```bash
kotobase lookup kanji-find [OPTIONS]
```

#### Options

| Option | Description |
| --- | --- |
| `-s / --stroke` | Required Stroke Count |
| `-g / --grade` | Required School Grade |
| `--skip` | SKIP Query Code, Such As `1-4-3` |
| `-f / --freq` | Maximum Newspaper Frequency Rank |
| `--jlpt` | Required Tanos JLPT Level |
| `-l / --limit` | Maximum Results (Default `30`) |
| `-j / --json` | Format Results As `JSON` |

#### Examples
```bash
kotobase lookup kanji-find --jlpt 5  # (1)!
kotobase lookup kanji-find -s 8 -g 2  # (2)!
kotobase lookup kanji-find --skip 1-4-3  # (3)!
```

1. Every Kanji In Tanos JLPT N5
2. Eight-Stroke Grade 2 Kanji
3. Kanji With The Given SKIP Code

### `lookup radicals`

Lists every search radical grouped by stroke count, or finds the kanji that contain every given radical

```bash
kotobase lookup radicals [RADICALS]... [OPTIONS]
```

#### Options

| Option | Description |
| --- | --- |
| `-j / --json` | Format Results As `JSON` |

#### Examples
```bash
kotobase lookup radicals  # (1)!
kotobase lookup radicals 言 五  # (2)!
```

1. List Every Search Radical Grouped By Stroke Count
2. Kanji Containing Both Radicals

### `lookup jlpt-list`

Shows a full Tanos JLPT study list for a kind and level

```bash
kotobase lookup jlpt-list KIND LEVEL [OPTIONS]
```

`KIND` is one of `vocab`, `kanji` or `grammar`, and `LEVEL` is `1` to `5`

#### Options

| Option | Description |
| --- | --- |
| `-j / --json` | Format Results As `JSON` |

#### Examples
```bash
kotobase lookup jlpt-list vocab 5  # (1)!
kotobase lookup jlpt-list kanji 3  # (2)!
kotobase lookup jlpt-list grammar 2  # (3)!
```

1. The Full N5 Vocabulary List
2. The Full N3 Kanji List
3. The Full N2 Grammar List

### `lookup names`

Looks up or browses JMnedict proper names

```bash
kotobase lookup names [FORM] [OPTIONS]
```

#### Options

| Option | Description |
| --- | --- |
| `-t / --type` | Browse A Name Type, Such As `place` |
| `-j / --json` | Format Results As `JSON` |

#### Examples
```bash
kotobase lookup names 田中  # (1)!
kotobase lookup names --type place  # (2)!
```

1. Search A Name By Its Form
2. Browse Every Name Of A Given Type

### `lookup meaning`

Finds dictionary entries by their English meaning, using the gloss full text index

```bash
kotobase lookup meaning QUERY [OPTIONS]
```

#### Options

| Option | Description |
| --- | --- |
| `-l / --limit` | Maximum Results (Default `30`) |
| `-j / --json` | Format Results As `JSON` |

#### Examples
```bash
kotobase lookup meaning "to eat"  # (1)!
kotobase lookup meaning eat -l 10  # (2)!
```

1. Entries Whose Gloss Matches The Query
2. Cap The Number Of Results

### `lookup sentences`

Finds Japanese example sentences containing a text, with their English translations

```bash
kotobase lookup sentences TEXT [OPTIONS]
```

#### Options

| Option | Description |
| --- | --- |
| `--limit` | Maximum Results (Default `10`) |
| `-j / --json` | Format Results As `JSON` |

#### Examples
```bash
kotobase lookup sentences 日本  # (1)!
kotobase lookup sentences 日本 --limit 20  # (2)!
```

1. Sentences Containing The Text
2. Show More Results

### `lookup furigana`

Shows the furigana segmentation for a written form

```bash
kotobase lookup furigana WORD [OPTIONS]
```

#### Options

| Option | Description |
| --- | --- |
| `-j / --json` | Format Result As `JSON` |

#### Examples
```bash
kotobase lookup furigana 食べる  # (1)!
```

1. The Spelling Aligned To Its Reading

### `lookup kanji-svg`

Prints a kanji's stroke order as a renderable SVG document, redirect it to a file to open in a browser

```bash
kotobase lookup kanji-svg LITERAL [OPTIONS]
```

#### Options

| Option | Description |
| --- | --- |
| `--raw` | Emit The Raw KanjiVG Fragment Instead Of A Renderable SVG |

#### Examples
```bash
kotobase lookup kanji-svg 春 > haru.svg  # (1)!
kotobase lookup kanji-svg 春 --raw  # (2)!
```

1. A Self-Contained SVG With A `109` View Box And Overridable Stroke Styling
2. The Original KanjiVG `<kanji>` Fragment, For KanjiVG-Specific Tooling

### `lookup audio`

Lists the pronunciation audio clips for a kanji or word, or downloads them with `-o`

```bash
kotobase lookup audio KEY [OPTIONS]
```

#### Options

| Option | Description |
| --- | --- |
| `-o / --out` | Directory To Save The Audio Clips Into |
| `-j / --json` | Format Result As `JSON` |

#### Examples
```bash
kotobase lookup audio 語  # (1)!
kotobase lookup audio 語 -o ./clips  # (2)!
```

1. List Every Bundled Clip With Its Reading, Format, Source And License
2. Save Each Clip Into `./clips` Named `<reading>.<format>`

???+ warning "Needs The Audio Pack"
    - The Actual Audio Data Lives In The Optional `Audio Pack`

    - Install It With `kotobase db pull --with-audio` Or `kotobase db build --with-audio`

## Database Commands

`kotobase db` Commands Build Or Download The Database

### `db info`

Shows the build metadata recorded in the active database

```bash
kotobase db info
```

#### Examples
```bash
kotobase db info  # (1)!
```

1. Schema Version, Build Date, Size And Source Versions

### `db build`

Downloads the upstream sources and builds the database locally

```bash
kotobase db build [OPTIONS]
```

#### Options

| Option | Description |
| --- | --- |
| `-f / --force` | Rebuild Even When A Database Already Exists |
| `--with-links / --no-links` | Align Tatoeba Sentences With English (Default On) |
| `--with-audio / --no-audio` | Also Build The Optional Audio Pack (Default On) |

#### Examples
```bash
kotobase db build  # (1)!
kotobase db build --no-audio  # (2)!
kotobase db build --force  # (3)!
```

1. Build The Core + Audio Databases
2. Build Only The Core Database
3. Rebuild Even If Present

### `db pull`

Downloads a prebuilt database from a GitHub Release

```bash
kotobase db pull [OPTIONS]
```

#### Options

| Option | Description |
| --- | --- |
| `-t / --tag` | Release Tag To Pull From (Default The Latest Release) |
| `--force` | Replace An Existing Database |
| `--with-audio / --no-audio` | Also Pull The Audio Pack (Default On) |

#### Examples
```bash
kotobase db pull  # (1)!
kotobase db pull --no-audio  # (2)!
kotobase db pull --tag v0.3.0  # (3)!
```

1. Pull The Core + Audio Databases
2. Pull Only The Core Database
3. Pull From A Specific Release

## Cache Commands

`kotobase cache` Commands Manage The Per-User Cache Directory That Holds The Databases And Downloaded Sources

### `cache clear`

Deletes the entire cache directory, or only specific items within it

```bash
kotobase cache clear [OPTIONS]
```

#### Options

| Option | Description |
| --- | --- |
| `-y / --yes` | Skip The Confirmation Prompt |
| `--sources-only` | Delete Only The Downloaded Raw Sources |
| `--db-only` | Delete Only The Built Or Pulled Databases |

#### Examples
```bash
kotobase cache clear  # (1)!
kotobase cache clear -y  # (2)!
kotobase cache clear --db-only  # (3)!
```

1. Delete Everything (Asks First)
2. Delete Everything Without Confirming
3. Delete Only The Databases

### `cache path`

Prints the file system path of the cache directory

```bash
kotobase cache path
```

#### Examples
```bash
kotobase cache path  # (1)!
```

1. The Resolved Cache Directory

### `cache size`

Shows a breakdown of the cache disk usage

```bash
kotobase cache size
```

#### Examples
```bash
kotobase cache size  # (1)!
```

1. Per-Item And Total Disk Usage

## Version

Prints the installed kotobase version

```bash
kotobase version
```
