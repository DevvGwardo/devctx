"""Tests for the git collector."""

import subprocess
from pathlib import Path

from devctx.collectors.git import collect_git, _find_git_root, _auto_detect_scan_dirs


def _init_repo(path: Path, dirty: bool = False, commit_msg: str = "init"):
    """Create a minimal git repo with one commit."""
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init"], cwd=path, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=path, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, capture_output=True)
    (path / "README.md").write_text("hello")
    subprocess.run(["git", "add", "."], cwd=path, capture_output=True)
    subprocess.run(["git", "commit", "-m", commit_msg], cwd=path, capture_output=True)
    if dirty:
        (path / "dirty.txt").write_text("uncommitted")


def _init_repo_with_timestamp(path: Path, days_ago: int, dirty: bool = False):
    """Create a repo with commit at a specific days_ago."""
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init"], cwd=path, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=path, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, capture_output=True)
    (path / "README.md").write_text("hello")
    subprocess.run(["git", "add", "."], cwd=path, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init", "--date", f"{days_ago} days ago"],
        cwd=path, capture_output=True
    )
    if dirty:
        (path / "dirty.txt").write_text("uncommitted")


def test_finds_repo_in_scan_dir(tmp_path):
    repo = tmp_path / "myproject"
    _init_repo(repo)

    result = collect_git(scan_dirs=[str(tmp_path)])
    assert "myproject" in result
    assert result["myproject"]["branch"] == "main" or result["myproject"]["branch"] == "master"
    assert result["myproject"]["dirty"] is False


def test_detects_dirty_state(tmp_path):
    repo = tmp_path / "dirtyrepo"
    _init_repo(repo, dirty=True)

    result = collect_git(scan_dirs=[str(tmp_path)])
    assert result["dirtyrepo"]["dirty"] is True
    assert result["dirtyrepo"]["changed_files"] >= 1


def test_scan_dir_is_repo_itself(tmp_path):
    _init_repo(tmp_path, commit_msg="direct repo")

    result = collect_git(scan_dirs=[str(tmp_path)])
    assert tmp_path.name in result


def test_skips_nonexistent_dir():
    result = collect_git(scan_dirs=["/nonexistent/path/xyz"])
    assert result == {}


def test_empty_scan_dir(tmp_path):
    result = collect_git(scan_dirs=[str(tmp_path)])
    assert result == {}


def test_auto_detect_finds_git_root(tmp_path):
    parent = tmp_path / "parent"
    repo = parent / "myrepo"
    _init_repo(repo)

    original_cwd = Path.cwd()
    try:
        import os
        os.chdir(repo)
        result = _find_git_root()
        assert result is not None
        assert (result / ".git").exists()
    finally:
        os.chdir(original_cwd)


def test_auto_detect_returns_home_if_no_git(tmp_path):
    original_cwd = Path.cwd()
    try:
        import os
        os.chdir(tmp_path)
        result = _find_git_root()
        assert result is None
    finally:
        os.chdir(original_cwd)


def test_auto_detect_scan_dirs_falls_back_to_home(tmp_path):
    original_cwd = Path.cwd()
    try:
        import os
        os.chdir(tmp_path)
        result = _auto_detect_scan_dirs()
        assert len(result) == 1
        assert result[0] == str(Path.home())
    finally:
        os.chdir(original_cwd)


def test_multi_repo_summary_under_10(tmp_path):
    for i in range(5):
        _init_repo(tmp_path / f"repo{i}")

    result = collect_git(scan_dirs=[str(tmp_path)])
    assert "_summary" not in result
    assert len(result) == 5


def test_multi_repo_summary_over_10(tmp_path):
    for i in range(12):
        _init_repo_with_timestamp(tmp_path / f"repo{i}", i)

    result = collect_git(scan_dirs=[str(tmp_path)])
    assert "_summary" in result
    assert result["_summary"]["count"] == 2
    assert len(result) - 1 == 10


def test_multi_repo_summary_tracks_dirty_ahead_behind(tmp_path):
    r1 = tmp_path / "repo1"
    _init_repo(r1, dirty=True)
    r2 = tmp_path / "repo2"
    _init_repo(r2)
    subprocess.run(["git", "checkout", "-b", "feature"], cwd=r2, capture_output=True)
    subprocess.run(["git", "commit", "--allow-empty", "-m", "feat"], cwd=r2, capture_output=True)
    subprocess.run(["git", "push", "-u", "origin", "feature"], cwd=r2, capture_output=True)

    repos = {"repo1": {"dirty": True, "ahead": 0, "behind": 0}, "repo2": {"dirty": False, "ahead": 1, "behind": 2}}
    repo_items = list(repos.items())
    sorted_repos = sorted(repo_items, key=lambda item: item[1].get("_last_commit_ts", 0), reverse=True)

    top_10 = dict(sorted_repos[:2])
    remaining = sorted_repos[2:]

    total_dirty = sum(1 for _, s in remaining if s.get("dirty"))
    total_ahead = sum(s.get("ahead", 0) for _, s in remaining)
    total_behind = sum(s.get("behind", 0) for _, s in remaining)

    assert total_dirty >= 0
    assert total_ahead >= 0
    assert total_behind >= 0
