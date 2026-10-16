"""Small, offline CLI surface for the orchestrator bootstrap."""

import argparse
import importlib
import shutil
import sys
from collections.abc import Sequence

from orchestrator import __version__


def doctor() -> int:
    """Report optional capabilities without creating state or running external tools."""
    git_status = "available" if shutil.which("git") else "unavailable (optional)"
    print(f"Git: {git_status}")
    try:
        sqlite = importlib.import_module("sqlite3")
    except ImportError:
        print("SQLite: unavailable (optional)")
    else:
        print(f"SQLite: available ({sqlite.sqlite_version})")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Parse arguments and return an exit code for either entry point."""
    parser = argparse.ArgumentParser(prog="orchestrator", description="Coding-agent orchestrator")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("version", help="Report the package version")
    commands.add_parser("doctor", help="Report optional local capabilities")
    validate = commands.add_parser("validate", help="Task validation (not implemented yet)")
    validate.add_argument("path", help="Task contract path")
    args = parser.parse_args(argv)
    if args.command == "version":
        print(__version__)
        return 0
    if args.command == "doctor":
        return doctor()
    print("Task validation is unsupported until ORCH-002; no file was read.", file=sys.stderr)
    return 2
