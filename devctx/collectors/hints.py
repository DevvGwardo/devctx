"""Generate agent-friendly hints from collected context."""

from __future__ import annotations

from typing import Any


def generate_hints(
    services: dict[str, Any],
    git: dict[str, Any],
    deploy: dict[str, Any],
    env: dict[str, Any],
) -> list[str]:
    hints: list[str] = []

    # Service hints
    ports = services.get("ports", {})
    if not any("hermes" in k for k in ports):
        hints.append("hermes-gateway is not running — start with `hermes gateway`")
    if not any("postgres" in k for k in ports):
        hints.append("postgres is not listening — check if the database is running")

    # Git hints
    for repo, state in git.items():
        if state.get("ahead", 0) > 0:
            hints.append(f"{repo} has {state['ahead']} unpushed commit(s) on {state['branch']}")
        if state.get("behind", 0) > 0:
            hints.append(f"{repo} is {state['behind']} commit(s) behind upstream on {state['branch']}")
        if state.get("dirty"):
            n = state.get("changed_files", "some")
            hints.append(f"{repo} has {n} uncommitted change(s)")

    # Env hints
    missing = env.get("missing", [])
    if missing:
        hints.append(f"missing env vars: {', '.join(missing)}")

    # Docker hints
    containers = services.get("docker", [])
    if containers:
        names = [c["name"] for c in containers]
        hints.append(f"{len(containers)} docker container(s) running: {', '.join(names)}")

    return hints
