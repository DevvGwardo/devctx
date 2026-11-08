"""Collect git state across project directories."""

from __future__ import annotations

from collections import Counter
import subprocess
from pathlib import Path
from typing import Any


def _find_git_root() -> Path | None:
    """Walk up from cwd to find the first .git entry (directory or worktree file)."""
    cwd = Path.cwd()
    for parent in [cwd] + list(cwd.parents):
        if (parent / ".git").exists():
            return parent
    return None


def _auto_detect_scan_dirs() -> list[str]:
    """Auto-detect scan scope: find git root or fall back to HOME."""
    git_root = _find_git_root()
    if git_root:
        return [str(git_root)]
    return [str(Path.home())]


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

    status_lines = _git(repo, "status", "--porcelain")
    dirty = None if status_lines is None else bool(status_lines)

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
    last_timestamp = _git(repo, "log", "-1", "--format=%ct") or ""

    state: dict[str, Any] = {
        "branch": branch,
        "dirty": dirty,
        "ahead": ahead,
        "behind": behind,
        "last_commit": last_msg,
        "last_commit_age": last_time,
    }
    if dirty is None:
        state["status_error"] = "git status failed or timed out"

    if last_timestamp:
        try:
            state["_last_commit_ts"] = int(last_timestamp)
        except ValueError:
            pass

    if dirty:
        state["changed_files"] = len([l for l in status_lines.split("\n") if l.strip()])

    return state


def collect_git(scan_dirs: list[str] | None = None) -> dict[str, Any]:
    if scan_dirs is None:
        scan_dirs = _auto_detect_scan_dirs()

    repos: dict[str, Any] = {}

    def add_repo(repo: Path) -> None:
        repo = repo.resolve()
        path = str(repo)
        if path not in repos:
            state = _repo_state(repo)
            if state:
                repos[path] = {**state, "path": path}

    for scan_dir in scan_dirs:
        base = Path(scan_dir).resolve()
        if not base.is_dir():
            continue

        if (base / ".git").exists():
            add_repo(base)
            continue

        try:
            for entry in sorted(base.iterdir()):
                if entry.is_dir() and not entry.name.startswith(".") and (entry / ".git").exists():
                    add_repo(entry)
        except PermissionError:
            continue

    if not repos:
        return repos

    # Keep ordinary names compatible, disambiguating all collisions by canonical path.
    names = Counter(Path(path).name for path in repos)
    repos = {
        Path(path).name if names[Path(path).name] == 1 and Path(path).name not in {"", "_summary"} else path: state
        for path, state in repos.items()
    }

    if len(repos) <= 10:
        for state in repos.values():
            state.pop("_last_commit_ts", None)
        return repos

    repo_items = list(repos.items())
    sorted_repos = sorted(
        repo_items,
        key=lambda item: item[1].get("_last_commit_ts", 0),
        reverse=True,
    )

    top_10 = dict(sorted_repos[:10])
    remaining = sorted_repos[10:]

    total_dirty = sum(1 for _, s in remaining if s.get("dirty"))
    total_unknown = sum(1 for _, s in remaining if s.get("dirty") is None)
    total_ahead = sum(s.get("ahead", 0) for _, s in remaining)
    total_behind = sum(s.get("behind", 0) for _, s in remaining)

    for state in top_10.values():
        state.pop("_last_commit_ts", None)

    top_10["_summary"] = {
        "count": len(remaining),
        "dirty": total_dirty,
        "unknown": total_unknown,
        "ahead": total_ahead,
        "behind": total_behind,
    }

    return top_10
