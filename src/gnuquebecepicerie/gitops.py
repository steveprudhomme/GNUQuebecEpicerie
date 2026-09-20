from __future__ import annotations

import subprocess
from pathlib import Path


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.strip()


def has_changes(repo: Path) -> bool:
    return bool(_git(repo, "status", "--porcelain"))


def commit_and_push(repo: Path, message: str) -> bool:
    """Commit et push uniquement lorsqu'il existe des changements locaux."""
    if not has_changes(repo):
        return False
    _git(repo, "add", "data")
    _git(repo, "commit", "-m", message)
    _git(repo, "push")
    return True
