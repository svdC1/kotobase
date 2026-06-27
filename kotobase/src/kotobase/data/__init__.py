"""
Centralized package data for :mod:`kotobase`

abstract: Scope
    - This sub-package holds the small, openly-licensed reference data that
      ships *inside* the wheel

    - Large, regenerable artifacts like the raw source downloads, build
      intermediates and the compiled SQLite database are **not** stored here

    - They live in a per-user cache directory resolved at runtime (see
      `kotobase.db_builder.config`)
"""

from __future__ import annotations

__all__: list[str] = []
