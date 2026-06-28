# Versioning Policy

Kotobase follows [`Semantic Versioning`](https://semver.org/)

## Semantic Versioning Summary

???+ abstract "Version Increments"
    ```
    MAJOR.MINOR.PATCH
    ```

    | Segment | Incremented When |
    |---------|-------------------|
    | `MAJOR` | A breaking change is introduced |
    | `MINOR` | A new backward-compatible functionality is added |
    | `PATCH` | A backward-compatible bug fix is implemented |

---

This page defines exactly what the `Public API` means, so you know what a
version bump protects

## What Is Public

The `Public API`, covered by this policy, is the surface re-exported from the
top-level `kotobase` package and the documented command line

???+ info "Public"
    Anything reachable from these and documented in the
    [`API Reference`](../reference/index.md) is something you can rely on

    - `kotobase.__version__`
    - The [`Kotobase`][kotobase.api.Kotobase] class and its documented methods
    - All [`DTOs`][kotobase.db.dtos]
    - The [`DatabaseNotFoundError`][kotobase.db.connection.DatabaseNotFoundError]
      and [`AudioDatabaseNotFoundError`][kotobase.db.connection.AudioDatabaseNotFoundError]
      exceptions
    - All `kotobase` CLI command names and their documented options

## What Is Not Public

???+ warning "Not Public"
    The following may change in any release, including patch releases, without being
    considered a breaking change

    - Internal Modules
    - [`models`][kotobase.db.models]
    - [`repos`][kotobase.db.repos]
    - [`uow`][kotobase.db.uow]
    - [`connection`][kotobase.db.connection]
    - [`builder`][kotobase.db.builder]
    - [`terminal_output`][kotobase.terminal_output]
    - The exact `CLI` output formatting and wording *(Only the `--json` shape + the commands and options are stable)*
    - The on-disk database file layout and any raw build artifacts

## Database Schema

The compiled database is versioned `independently` of the package

Its format is recorded in the `db_meta` table as a `schema_version`, which you can see with
`kotobase db info`

???+ warning "Public API + Database Versions"
    A database must match the `schema` that the installed `kotobase` API expects, therefore a `schema_version`
    change is `ALWAYS` considered a `Breaking Change` and released alongside a new `MAJOR` version *(starting from 1.0.0)*

## Deprecations

After `1.0.0`, when a `Public API` element is going to be removed, it is first `deprecated`

The deprecation is announced in the [`Changelog`](changelog.md), the element keeps
working for at least one minor release, and it emits a warning where practical
before it is removed in a later release
