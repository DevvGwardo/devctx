"""Collect git state across project directories."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any


def _git(repo: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except subprocess.TimeoutExpired:
        pass
    return None


def _repo_state(repo: Path) -> dict[str, Any] | None:
    branch = _git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    if branch is None:
        return None

    status_lines = _git(repo, "status", "--porcelain") or ""
    dirty = len([l for l in status_lines.split("\n") if l.strip()]) > 0

    ahead = 0
    behind = 0
    tracking = _git(repo, "rev-parse", "--abbrev-ref", "@{upstream}")
    if tracking:
        count = _git(repo, "rev-list", "--left-right", "--count", f"{tracking}...HEAD")
        if count:
            parts = count.split("\t")
            if len(parts) == 2:
                behind, ahead = int(parts[0]), int(parts[1])

    last_msg = _git(repo, "log", "-1", "--format=%s") or ""
    last_time = _git(repo, "log", "-1", "--format=%cr") or ""

    state: dict[str, Any] = {
        "branch": branch,
        "dirty": dirty,
        "ahead": ahead,
        "behind": behind,
        "last_commit": last_msg,
        "last_commit_age": last_time,
    }

    if dirty:
        state["changed_files"] = len([l for l in status_lines.split("\n") if l.strip()])

    return state


def collect_git(scan_dirs: list[str] | None = None) -> dict[str, Any]:
    if scan_dirs is None:
        home = Path.home()
        scan_dirs = [str(home)]

    repos: dict[str, Any] = {}

    for scan_dir in scan_dirs:
        base = Path(scan_dir)
        if not base.is_dir():
            continue

        # Check if the scan_dir itself is a repo
        if (base / ".git").exists():
            state = _repo_state(base)
            if state:
                repos[base.name] = state
            continue

        # Scan one level deep
        try:
            for entry in sorted(base.iterdir()):
                if entry.is_dir() and not entry.name.startswith(".") and (entry / ".git").exists():
                    state = _repo_state(entry)
                    if state:
                        repos[entry.name] = state
        except PermissionError:
            continue

    return repos
