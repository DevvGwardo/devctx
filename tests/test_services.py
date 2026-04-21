"""Tests for the services collector."""

from unittest.mock import patch, MagicMock

from devctx.collectors.services import collect_services, _check_port, _get_docker_containers


def test_check_port_closed():
    # A random high port should not be listening
    assert _check_port(59123) is False


def test_collect_services_returns_ports_key():
    result = collect_services()
    assert "ports" in result
    assert isinstance(result["ports"], dict)


@patch("devctx.collectors.services._check_port", return_value=True)
@patch("devctx.collectors.services._get_pid_on_port", return_value=1234)
def test_collect_services_with_listening_port(mock_pid, mock_port):
    result = collect_services()
    # At least one port should appear since _check_port always returns True
    assert len(result["ports"]) > 0
    # Each entry should have expected fields
    for entry in result["ports"].values():
        assert "port" in entry
        assert "status" in entry
        assert entry["status"] == "listening"


@patch("devctx.collectors.services._check_port", return_value=False)
def test_collect_services_no_ports(mock_port):
    result = collect_services()
    assert result["ports"] == {}


@patch("devctx.collectors.services.shutil.which", return_value=None)
def test_docker_containers_no_docker(mock_which):
    assert _get_docker_containers() == []


@patch("devctx.collectors.services.shutil.which", return_value="/usr/bin/docker")
@patch("devctx.collectors.services.subprocess.run")
def test_docker_containers_parses_output(mock_run, mock_which):
    mock_run.return_value = MagicMock(
        returncode=0,
        stdout='{"Names":"redis","Image":"redis:7","Status":"Up 2 hours","Ports":"6379/tcp"}\n',
    )
    containers = _get_docker_containers()
    assert len(containers) == 1
    assert containers[0]["name"] == "redis"
    assert containers[0]["image"] == "redis:7"
