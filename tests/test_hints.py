"""Tests for the hints generator."""

from devctx.collectors.hints import generate_hints


def test_empty_inputs():
    hints = generate_hints({}, {}, {}, {})
    # Should still generate default hints for missing services
    assert isinstance(hints, list)
    assert any("hermes" in h for h in hints)
    assert any("postgres" in h for h in hints)


def test_no_hermes_hint():
    services = {"ports": {"vite": {"port": 5173}}}
    hints = generate_hints(services, {}, {}, {})
    assert any("hermes-gateway is not running" in h for h in hints)


def test_hermes_running_no_hint():
    services = {"ports": {"hermes-gateway": {"port": 8642}}}
    hints = generate_hints(services, {}, {}, {})
    assert not any("hermes-gateway is not running" in h for h in hints)


def test_git_ahead_hint():
    git = {"myrepo": {"branch": "main", "ahead": 3, "behind": 0, "dirty": False}}
    hints = generate_hints({}, git, {}, {})
    assert any("myrepo" in h and "3 unpushed" in h for h in hints)


def test_git_behind_hint():
    git = {"myrepo": {"branch": "main", "ahead": 0, "behind": 2, "dirty": False}}
    hints = generate_hints({}, git, {}, {})
    assert any("myrepo" in h and "2 commit(s) behind" in h for h in hints)


def test_git_dirty_hint():
    git = {"myrepo": {"branch": "dev", "ahead": 0, "behind": 0, "dirty": True, "changed_files": 5}}
    hints = generate_hints({}, git, {}, {})
    assert any("myrepo" in h and "5 uncommitted" in h for h in hints)


def test_missing_env_hint():
    env = {"set": [], "missing": ["ANTHROPIC_API_KEY", "OPENAI_API_KEY"]}
    hints = generate_hints({}, {}, {}, env)
    assert any("missing env vars" in h for h in hints)
    assert any("ANTHROPIC_API_KEY" in h for h in hints)


def test_docker_hint():
    services = {"ports": {}, "docker": [{"name": "redis"}, {"name": "postgres"}]}
    hints = generate_hints(services, {}, {}, {})
    assert any("2 docker container(s)" in h for h in hints)
