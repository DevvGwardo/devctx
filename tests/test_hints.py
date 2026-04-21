"""Tests for the hints generator."""

from devctx.collectors.hints import generate_hints


def test_empty_inputs():
    hints = generate_hints({}, {}, {}, {})
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


def test_hints_cap_at_15():
    git = {}
    for i in range(20):
        git[f"repo{i}"] = {"branch": "main", "ahead": 1, "behind": 0, "dirty": True, "changed_files": 1}

    hints = generate_hints({}, git, {}, {})
    full_hints = [h for h in hints if "more repo(s)" not in h]
    assert len(full_hints) <= 15


def test_hints_bucketing():
    git = {}
    for i in range(20):
        git[f"repo{i}"] = {"branch": "main", "ahead": 1, "behind": 0, "dirty": True, "changed_files": 1}

    hints = generate_hints({}, git, {}, {})
    assert any("more repo(s)" in h for h in hints)


def test_hints_priority_order():
    git = {f"repo{i}": {"branch": "main", "ahead": 1, "behind": 1, "dirty": True, "changed_files": 1} for i in range(20)}
    services = {"ports": {}}
    hints = generate_hints(services, git, {}, {})

    service_hint = [h for h in hints if "hermes" in h or "postgres" in h]
    if service_hint:
        assert hints[0] == service_hint[0] or "hermes" in hints[0] or "postgres" in hints[0]
