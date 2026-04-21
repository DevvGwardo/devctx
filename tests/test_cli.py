"""Tests for the CLI snapshot function."""

from unittest.mock import patch

from devctx.cli import snapshot


@patch("devctx.cli.collect_services", return_value={"ports": {}})
@patch("devctx.cli.collect_git", return_value={})
@patch("devctx.cli.collect_deploy", return_value={})
@patch("devctx.cli.collect_env", return_value={"set": [], "missing": []})
def test_snapshot_all_sections(mock_env, mock_deploy, mock_git, mock_svc):
    result = snapshot()
    assert "version" in result
    assert "timestamp" in result
    assert "services" in result
    assert "git" in result
    assert "deploy" in result
    assert "env" in result
    assert "hints" in result


@patch("devctx.cli.collect_services", return_value={"ports": {}})
def test_snapshot_single_section(mock_svc):
    result = snapshot(sections=["services"])
    assert "services" in result
    assert "git" not in result
    assert "deploy" not in result


@patch("devctx.cli.collect_git", return_value={"myrepo": {"branch": "main", "dirty": False}})
def test_snapshot_git_only(mock_git):
    result = snapshot(sections=["git"])
    assert "git" in result
    assert "myrepo" in result["git"]
    assert "services" not in result


def test_snapshot_version_and_timestamp():
    result = snapshot(sections=[])  # empty sections = nothing collected
    assert "version" in result
    assert "timestamp" in result


@patch("devctx.cli.collect_services", return_value={"ports": {"postgres": {"port": 5432}}})
@patch("devctx.cli.collect_git", return_value={})
@patch("devctx.cli.collect_deploy", return_value={})
@patch("devctx.cli.collect_env", return_value={"set": [], "missing": []})
def test_snapshot_hints_force_collects_dependencies(mock_env, mock_deploy, mock_git, mock_svc):
    # Asking for hints alone must still run every collector so hints have real data,
    # but the output stays scoped to "hints".
    result = snapshot(sections=["hints"])
    assert "hints" in result
    assert "services" not in result
    assert "git" not in result
    mock_svc.assert_called_once()
    mock_git.assert_called_once()
    mock_deploy.assert_called_once()
    mock_env.assert_called_once()
    # postgres is listening in the mocked services — the false-negative hint must NOT fire.
    assert not any("postgres is not listening" in h for h in result["hints"])
