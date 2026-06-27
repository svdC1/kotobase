# Changelog

All notable changes to this project are documented here

The format is based on [`Keep a Changelog`](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [`Semantic Versioning`](versioning.md)

## [`0.3.0`](https://github.com/svdC1/kotobase/releases/tag/v0.3.0) - 2026-06-26

A full rewrite of the package, its data and its tooling

`0.2.7` shipped a flatter database covering `JMdict`, `JMnedict`, `KanjiDic2`, Japanese-Only `Tatoeba`
sentences and the `Tanos JLPT` lists, distributed through `Google Drive`

### Added

- **New Data Sources** &rarr; `KRADFILE` / `RADKFILE` for kanji to
  radical decomposition and radical search, `JmdictFurigana` for per-form
  furigana, `KanjiVG` for stroke-order SVG, and an optional `Kanji Alive`
  pronunciation audio pack

- **`Tatoeba`** &rarr; Now imports the links and English exports as well, aligning Japanese
  sentences with their English translations

- **Full `JMdict` + `JMnedict` Tag Extraction** &rarr; `part of speech`, `register`
  *(slang, colloquial, ...)*, `field`, `dialect` and `priority tags` that the previous
  subset discarded

- **New API Methods On `Kotobase`** &rarr; `search_kanji`, `kanji_by_skip`, `stroke_svg`,
  `radicals`, `by_radicals`, `jlpt_list`, `names`, `furigana`, `audio`,
  `audio_bytes`, `save_audio`, `search_meaning` and `expand_tags`

- **New `CLI` Commands Grouped Into `lookup`, `db` and `cache`** &rarr; `lookup all`,
  `kanji-find`, `radicals`, `jlpt-list`, `names`, `meaning`, `sentences`,
  `furigana`, `kanji-svg`, `audio`, `cache path` / `size` / `clear`

- **`dev` + `docs` Optional-Dependency Extras** &rarr; `ruff` / `mypy` / pre-commit
  tooling, and a shipped `py.typed` marker

### Changed

- The `CLI` is rebuilt on `Typer` and `Rich`, with panelled output and `--json` on
  query commands. The entry point moved from `kotobase.cli:main` to
  `kotobase.cli:app`

- The database is distributed through `GitHub Releases` as zstandard-compressed
  assets, rebuilt weekly, replacing the `Google Drive` distribution

- The `schema` is normalized *(child tables and a JSON column for read-only tag
  blobs)* instead of the previous flat tables with delimited-string columns, and
  the build streams the raw `EDRDG` and `Tatoeba` sources straight into `SQLite`

- Reads go through a `thread-safe`, `read-only` engine and return immutable,
  serializable data objects built with `from_orm` classmethods

- The package is consolidated under `db/` *(`connection`, `dtos`, `repos`,
  `uow`, `models`, `builder`)*. The old `core/`, `repos/` and `db_builder/`
  packages and `db/database.py` were restructured into it

- The minimum `Python` version is raised to `3.10`, with a modernized
  `pyproject.toml` *(full metadata and classifiers, including `Typing :: Typed`)*

### Removed

- The `Google Drive` distribution and the `gdown` dependency

- The `alembic` dependency. The compiled database now records its format in a
  `db_meta` schema version instead of migrations

- The `click` dependency, replaced by `Typer`

- `MANIFEST.in`, replaced by declarative package data

## [`0.2.7`](https://github.com/svdC1/kotobase/releases/tag/v0.2.7) - 2025-06-27

The final release of the `original line`

Had a flatter `SQLite` database distributed through `Google Drive` and queried with a `Click` CLI

The changelog for this and piror releases is documented only in the [`GitHub Releases`](https://github.com/svdC1/kotobase/releases/tag/) section
