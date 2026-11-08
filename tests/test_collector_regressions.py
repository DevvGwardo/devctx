"""Synthetic collector regressions: no host probes, live CLIs, or user repositories."""
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from devctx.cli import snapshot
from devctx.collectors.git import collect_git, _repo_state
from devctx.collectors.hints import generate_hints
from devctx.mcp_server import handle_request


@pytest.mark.parametrize("error", [FileNotFoundError("lsof missing"), PermissionError("lsof denied")])
def test_optional_pid_errors_preserve_service_snapshot_and_mcp(error):
    with patch("devctx.collectors.services.KNOWN_PORTS", {3000: "dev-server"}), \
         patch("devctx.collectors.services._check_port", return_value=True), \
         patch("devctx.collectors.services._get_docker_containers", return_value=[]), \
         patch("devctx.collectors.services.subprocess.run", side_effect=error):
        state = snapshot(sections=["services"])
        response = handle_request({
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": "get_dev_context", "arguments": {"sections": ["services"]}},
        })
    for result in (state, json.loads(response["result"]["content"][0]["text"])):
        entry = result["services"]["ports"]["dev-server"]
        assert entry["status"] == "listening"
        assert "pid" not in entry


@pytest.mark.parametrize("failure", ["timeout", "nonzero"])
def test_status_failure_is_unknown_and_visible_in_hints(failure):
    def fake_run(args, **kwargs):
        command = args[3:]
        if command == ["status", "--porcelain"]:
            if failure == "timeout":
                raise subprocess.TimeoutExpired(args, 10)
            return SimpleNamespace(returncode=128, stdout="", stderr="synthetic status failure")
        outputs = {
            ("rev-parse", "--abbrev-ref", "HEAD"): "main\n",
            ("log", "-1", "--format=%s"): "synthetic\n",
            ("log", "-1", "--format=%cr"): "1 day ago\n",
            ("log", "-1", "--format=%ct"): "100\n",
        }
        stdout = outputs.get(tuple(command))
        return SimpleNamespace(returncode=0 if stdout is not None else 1,
                               stdout=stdout or "", stderr="")
    with patch("devctx.collectors.git.subprocess.run", side_effect=fake_run):
        state = _repo_state(Path("/synthetic/repo"))
    assert state["dirty"] is None
    assert state["status_error"]
    assert "changed_files" not in state
    assert any("unknown" in hint and "repo" in hint
               for hint in generate_hints({}, {"repo": state}, {}, {}))


def test_repository_keys_preserve_collisions_and_canonical_provenance(tmp_path):
    for dirname in ("projects", "work"):
        (tmp_path / dirname / "api" / ".git").mkdir(parents=True)
    (tmp_path / "projects" / "ordinary" / ".git").mkdir(parents=True)
    (tmp_path / "projects" / "_summary" / ".git").mkdir(parents=True)
    (tmp_path / "projects" / "alias").symlink_to(tmp_path / "projects" / "api", target_is_directory=True)

    def fake_state(repo):
        dirty = repo.parent.name == "projects"
        return {"branch": "feature" if dirty else "main", "dirty": dirty,
                "ahead": 0, "behind": 0, **({"changed_files": 3} if dirty else {})}

    with patch("devctx.collectors.git._repo_state", side_effect=fake_state):
        result = collect_git([str(tmp_path / "projects"), str(tmp_path / "work"),
                              str(tmp_path / "projects" / "api")])
    assert len(result) == 4
    left, right = (str((tmp_path / dirname / "api").resolve()) for dirname in ("projects", "work"))
    assert result[left]["dirty"] is True
    assert result[right]["dirty"] is False
    assert result[left]["path"] == left
    assert result[right]["path"] == right
    assert result["ordinary"]["path"] == str((tmp_path / "projects" / "ordinary").resolve())
    assert "_summary" not in result


def test_truncated_repositories_count_unknown_status_separately(tmp_path):
    for index in range(11):
        (tmp_path / f"repo{index:02d}" / ".git").mkdir(parents=True)

    def fake_state(repo):
        index = int(repo.name[-2:])
        return {"branch": "main", "dirty": None if index == 10 else False,
                "status_error": "git status failed" if index == 10 else "",
                "ahead": 0, "behind": 0, "_last_commit_ts": 100 - index}

    with patch("devctx.collectors.git._repo_state", side_effect=fake_state):
        result = collect_git([str(tmp_path)])
    assert result["_summary"]["dirty"] == 0
    assert result["_summary"]["unknown"] == 1
    assert any("unknown" in hint for hint in generate_hints({}, result, {}, {}))
