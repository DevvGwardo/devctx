"""Tests for the deploy collector."""

import json
from unittest.mock import patch, MagicMock
from pathlib import Path

from devctx.collectors.deploy import collect_deploy, _railway_projects, _digitalocean_status


def test_collect_deploy_returns_dict():
    result = collect_deploy()
    assert isinstance(result, dict)


@patch("devctx.collectors.deploy.shutil.which", return_value=None)
def test_digitalocean_no_doctl(mock_which):
    assert _digitalocean_status() is None


@patch("devctx.collectors.deploy.shutil.which", return_value="/usr/bin/doctl")
@patch("devctx.collectors.deploy.subprocess.run")
def test_digitalocean_parses_droplets(mock_run, mock_which):
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout="12345    my-droplet    active    1.2.3.4    nyc1\n",
    )
    result = _digitalocean_status()
    assert result is not None
    assert len(result["droplets"]) == 1
    assert result["droplets"][0]["name"] == "my-droplet"
    assert result["droplets"][0]["status"] == "active"


def test_railway_projects_no_config(tmp_path):
    with patch("devctx.collectors.deploy.Path.home", return_value=tmp_path):
        assert _railway_projects() is None


def test_railway_projects_with_config(tmp_path):
    railway_dir = tmp_path / ".railway"
    railway_dir.mkdir()
    config = {
        "projects": {
            "/home/user/myapp": {"name": "myapp", "projectId": "abc-123"}
        }
    }
    (railway_dir / "config.json").write_text(json.dumps(config))

    with patch("devctx.collectors.deploy.Path.home", return_value=tmp_path):
        with patch("devctx.collectors.deploy.shutil.which", return_value=None):
            result = _railway_projects()
            assert result is not None
            assert len(result["projects"]) == 1
            assert result["projects"][0]["name"] == "myapp"
