"""
Tests for the command-line interface

Tests the database pull wiring, JSON output and the global error boundary that
renders Kotobase errors as messages
"""

from __future__ import annotations

import sys
from typing import Any

import pytest
from typer.testing import CliRunner

from kotobase import cli
from kotobase.exceptions import DatabaseNotFoundError

runner = CliRunner()


def test_db_pull_pulls_audio_instead_of_building(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """
    `db pull` downloads the audio pack rather than rebuilding it
    """
    calls: list[str] = []
    monkeypatch.setattr(
        cli.builder, "pull_db", lambda **kw: calls.append("pull_db")
    )
    monkeypatch.setattr(
        cli.builder, "pull_audio", lambda **kw: calls.append("pull_audio")
    )
    monkeypatch.setattr(
        cli.builder, "build_audio", lambda **kw: calls.append("build_audio")
    )
    result = runner.invoke(cli.app, ["db", "pull"])
    assert result.exit_code == 0
    assert "pull_audio" in calls
    assert "build_audio" not in calls


def test_lookup_json_keeps_japanese_verbatim(kb: object) -> None:
    """
    The --json output is valid and keeps Japanese text unescaped
    """
    result = runner.invoke(cli.app, ["lookup", "all", "日本語", "-j"])
    assert result.exit_code == 0
    assert "日本語" in result.output
    assert "\\u" not in result.output


def test_main_renders_kotobase_errors(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """
    main() renders any KotobaseError and exits non-zero, no traceback
    """

    def boom() -> Any:
        raise DatabaseNotFoundError("missing")

    monkeypatch.setattr(cli, "app", boom)
    monkeypatch.setattr(sys, "argv", ["kotobase"])
    with pytest.raises(SystemExit) as exc_info:
        cli.main()
    assert exc_info.value.code == 1
    assert "Database" in capsys.readouterr().out
