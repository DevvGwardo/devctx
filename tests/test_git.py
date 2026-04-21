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
    """Create a repo with both author and committer date at a specific days_ago."""
    import os as _os
    from datetime import datetime, timedelta, timezone
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init"], cwd=path, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=path, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, capture_output=True)
    (path / "README.md").write_text("hello")
    subprocess.run(["git", "add", "."], cwd=path, capture_output=True)
    dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
    iso = dt.strftime("%Y-%m-%dT%H:%M:%S+00:00")
    env = _os.environ.copy()
    env["GIT_AUTHOR_DATE"] = iso
    env["GIT_COMMITTER_DATE"] = iso
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=path, capture_output=True, env=env,
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


def test_multi_repo_summary_tracks_dirty(tmp_path):
    for i in range(11):
        _init_repo_with_timestamp(tmp_path / f"repo{i:02d}", days_ago=i, dirty=(i >= 10))

    result = collect_git(scan_dirs=[str(tmp_path)])
    assert "_summary" in result
    assert result["_summary"]["count"] == 1
    assert result["_summary"]["dirty"] == 1


def test_multi_repo_summary_tracks_ahead_behind(tmp_path):
    # Build 11 repos total. The oldest (repo10) is a clone with real
    # ahead+behind divergence from its upstream; the other 10 are
    # throwaway repos with more recent commits so repo10 gets pushed
    # into the _summary bucket.
    bare = tmp_path / "origin.git"
    subprocess.run(
        ["git", "init", "--bare", "--initial-branch=main", str(bare)],
        capture_output=True,
    )

    # Seed origin with one commit from a scratch clone.
    seed = tmp_path / "seed"
    subprocess.run(["git", "clone", str(bare), str(seed)], capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=seed, capture_output=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=seed, capture_output=True)
    subprocess.run(["git", "checkout", "-b", "main"], cwd=seed, capture_output=True)
    (seed / "a").write_text("a")
    subprocess.run(["git", "add", "."], cwd=seed, capture_output=True)
    subprocess.run(["git", "commit", "-m", "seed"], cwd=seed, capture_output=True)
    subprocess.run(["git", "push", "-u", "origin", "main"], cwd=seed, capture_output=True)

    # Clone becomes repo10 — oldest (furthest back days_ago).
    repo10 = tmp_path / "repo10"
    subprocess.run(["git", "clone", str(bare), str(repo10)], capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=repo10, capture_output=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=repo10, capture_output=True)
    # Add 2 local commits ahead.
    for n in range(2):
        (repo10 / f"local{n}").write_text("x")
        subprocess.run(["git", "add", "."], cwd=repo10, capture_output=True)
        subprocess.run(["git", "commit", "-m", f"local{n}"], cwd=repo10, capture_output=True)
    # Push 3 commits to origin from seed (so repo10 is behind by 3).
    for n in range(3):
        (seed / f"upstream{n}").write_text("y")
        subprocess.run(["git", "add", "."], cwd=seed, capture_output=True)
        subprocess.run(["git", "commit", "-m", f"upstream{n}"], cwd=seed, capture_output=True)
    subprocess.run(["git", "push"], cwd=seed, capture_output=True)
    subprocess.run(["git", "fetch"], cwd=repo10, capture_output=True)

    # 10 other repos — recent commits so they outrank repo10 in top-10.
    for i in range(10):
        _init_repo_with_timestamp(tmp_path / f"repo{i:02d}", days_ago=0)

    # Clean up bare + seed so they don't count as repos in the scan.
    import shutil as _sh
    _sh.rmtree(bare)
    _sh.rmtree(seed)

    result = collect_git(scan_dirs=[str(tmp_path)])
    assert "_summary" in result
    assert result["_summary"]["count"] == 1
    assert result["_summary"]["ahead"] == 2
    assert result["_summary"]["behind"] == 3


def test_last_commit_ts_stripped_single_repo_mode(tmp_path):
    for i in range(3):
        _init_repo(tmp_path / f"repo{i}")

    result = collect_git(scan_dirs=[str(tmp_path)])
    for name, state in result.items():
        if name == "_summary":
            continue
        assert "_last_commit_ts" not in state


def test_last_commit_ts_stripped_multi_repo_mode(tmp_path):
    for i in range(12):
        _init_repo_with_timestamp(tmp_path / f"repo{i:02d}", days_ago=i)

    result = collect_git(scan_dirs=[str(tmp_path)])
    for name, state in result.items():
        if name == "_summary":
            continue
        assert "_last_commit_ts" not in state


def test_find_git_root_handles_worktree_file(tmp_path, monkeypatch):
    main_repo = tmp_path / "main"
    _init_repo(main_repo)
    worktree = tmp_path / "wt"
    subprocess.run(
        ["git", "worktree", "add", "-b", "wt-branch", str(worktree)],
        cwd=main_repo, capture_output=True,
    )
    assert (worktree / ".git").is_file(), "worktree should have .git as a file"

    monkeypatch.chdir(worktree)
    root = _find_git_root()
    assert root is not None
    assert root == worktree


def test_find_git_root_stops_at_filesystem_root(monkeypatch):
    monkeypatch.chdir("/")
    result = _find_git_root()
    assert result is None
