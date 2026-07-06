"""CLI smoke tests."""

from __future__ import annotations

import subprocess
import sys

import pytest

import okf_kit


def test_version_constant():
    assert okf_kit.__version__


def test_cli_version(capsys):
    from okf_kit.cli import main

    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert okf_kit.__version__ in capsys.readouterr().out


def test_cli_help_exits_zero():
    result = subprocess.run(
        [sys.executable, "-m", "okf_kit.cli", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "build" in result.stdout


def test_later_command_reports_milestone(capsys):
    from okf_kit.cli import main

    assert main(["chat", "x"]) == 2
    assert "M3" in capsys.readouterr().err
