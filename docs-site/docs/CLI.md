# CLI

The `kotobase` command provides several subcommands for different types of lookups.

## General Lookup

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

## Kanji Lookup

To get information about a specific kanji character:

```bash
kotobase kanji 語
```

This will display the kanji's grade, stroke count, meanings, on'yomi, and kun'yomi readings, and JLPT level.

## JLPT Lookup

To check the JLPT level for a word or kanji:

```bash
kotobase jlpt 勉強
```

## Database

Kotobase relies on a local SQLite database.

You can also build it from the source files yourself.

The following commands are available for managing the database:

```bash
kotobase pull-db
```
> Downloads the pre-built SQLite database from a public [`Google Drive Folder`](https://drive.google.com/drive/u/0/folders/14wbgMyp0TubFyFaUy0W_CnK9_z7fo_Fv). This file is overwritten every week with a rebuilt database from updated sources. The rebuilding and overwriting is managed by a GitHub action in this repository.

```bash
kotobase build
```
> Builds the SQLite database from the raw source files. This will download the latest version of the source files (_Except Tanos JLPT lists which are shipped with the package itself._) and build the database locally.
