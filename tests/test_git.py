"""Tests for the git collector."""

import subprocess
from pathlib import Path

from devctx.collectors.git import collect_git


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
