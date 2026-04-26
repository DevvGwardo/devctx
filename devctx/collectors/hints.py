"""Generate agent-friendly hints from collected context."""

from __future__ import annotations

from typing import Any


def generate_hints(
    services: dict[str, Any],
    git: dict[str, Any],
    deploy: dict[str, Any],
    env: dict[str, Any],
) -> list[str]:
    MAX_FULL_HINTS = 15

    priority_hints: list[tuple[int, str]] = []

    ports = services.get("ports", {})
    if not any("hermes" in k for k in ports):
        priority_hints.append((0, "hermes-gateway is not running — start with `hermes gateway`"))
    if not any("postgres" in k for k in ports):
        priority_hints.append((0, "postgres is not listening — check if the database is running"))

    for repo, state in git.items():
        if repo == "_summary":
            continue
        branch = state.get("branch", "unknown")
        if state.get("behind", 0) > 0:
            priority_hints.append((1, f"{repo} is {state['behind']} commit(s) behind upstream on {branch}"))
        if state.get("ahead", 0) > 0:
            priority_hints.append((2, f"{repo} has {state['ahead']} unpushed commit(s) on {branch}"))
        if state.get("dirty"):
            n = state.get("changed_files", "some")
            priority_hints.append((3, f"{repo} has {n} uncommitted change(s)"))

    missing = env.get("missing", [])
    if missing:
        priority_hints.append((4, f"missing env vars: {', '.join(missing)}"))

    containers = services.get("docker", [])
    if containers:
        names = [c["name"] for c in containers]
        priority_hints.append((5, f"{len(containers)} docker container(s) running: {', '.join(names)}"))

    priority_hints.sort(key=lambda x: x[0])

    if len(priority_hints) <= MAX_FULL_HINTS:
        return [h for _, h in priority_hints]

    full_hints = [h for _, h in priority_hints[:MAX_FULL_HINTS]]

    behind_bucket = sum(1 for p, _ in priority_hints[MAX_FULL_HINTS:] if p == 1)
    ahead_bucket = sum(1 for p, _ in priority_hints[MAX_FULL_HINTS:] if p == 2)
    dirty_bucket = sum(1 for p, _ in priority_hints[MAX_FULL_HINTS:] if p == 3)
    missing_bucket = sum(1 for p, _ in priority_hints[MAX_FULL_HINTS:] if p == 4)

    buckets = []
    if behind_bucket > 0:
        buckets.append(f"{behind_bucket} more repo(s) behind upstream")
    if ahead_bucket > 0:
        buckets.append(f"{ahead_bucket} more repo(s) with unpushed commits")
    if dirty_bucket > 0:
        buckets.append(f"{dirty_bucket} more repo(s) have uncommitted changes")
    if missing_bucket > 0:
        buckets.append(f"{missing_bucket} more missing env var group(s)")

    full_hints.extend(buckets)

    return full_hints
