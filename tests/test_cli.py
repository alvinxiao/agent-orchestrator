"""Offline smoke tests against the installed package and both entry points."""

import importlib.metadata
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

import orchestrator
from orchestrator.cli import main


def run_cli(*args: str, module: bool = True) -> subprocess.CompletedProcess[str]:
    command = (
        [sys.executable, "-m", "orchestrator"]
        if module
        else [str(Path(sys.executable).with_name("orchestrator"))]
    )
    return subprocess.run(command + list(args), capture_output=True, text=True, timeout=10)


def test_import_and_distribution_version() -> None:
    assert orchestrator.__version__ == "0.1.0"
    assert importlib.metadata.version("agent-orchestrator") == orchestrator.__version__


@pytest.mark.parametrize("module", [True, False])
def test_help(module: bool) -> None:
    result = run_cli("--help", module=module)
    assert result.returncode == 0
    assert all(name in result.stdout for name in ("version", "doctor", "validate"))
    assert result.stderr == ""


@pytest.mark.parametrize("module", [True, False])
def test_version(module: bool) -> None:
    result = run_cli("version", module=module)
    assert result.returncode == 0
    assert result.stdout == "0.1.0\n"
    assert result.stderr == ""


def test_doctor() -> None:
    result = run_cli("doctor")
    assert result.returncode == 0
    assert "Git:" in result.stdout
    assert "SQLite:" in result.stdout


def test_doctor_without_optional_capabilities(capsys: pytest.CaptureFixture[str]) -> None:
    with (
        patch("orchestrator.cli.shutil.which", return_value=None),
        patch("orchestrator.cli.importlib.import_module", side_effect=ImportError),
    ):
        assert main(["doctor"]) == 0
    output = capsys.readouterr().out
    assert "Git: unavailable (optional)" in output
    assert "SQLite: unavailable (optional)" in output


def test_validate_missing_file(tmp_path: Path) -> None:
    path = tmp_path / "missing.yaml"
    result = run_cli("validate", str(path))
    assert result.returncode == 2
    assert json.loads(result.stdout)["errors"][0]["code"] == "read_error"
    assert result.stderr == ""
    assert not path.exists()


@pytest.mark.parametrize("args", [[], ["unknown"], ["validate"], ["version", "extra"]])
def test_invalid_arguments(args: list[str]) -> None:
    result = run_cli(*args)
    assert result.returncode == 2
    assert "usage:" in result.stderr
