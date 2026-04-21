"""devctx CLI — one command, full project context."""

from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Any

from devctx import __version__
from devctx.collectors import (
    collect_deploy,
    collect_env,
    collect_git,
    collect_services,
    generate_hints,
)


def snapshot(
    sections: list[str] | None = None,
    scan_dirs: list[str] | None = None,
    extra_env: list[str] | None = None,
) -> dict[str, Any]:
    all_sections = sections or ["services", "git", "deploy", "env", "hints"]

    result: dict[str, Any] = {"version": __version__, "timestamp": time.time()}

    services: dict[str, Any] = {}
    git: dict[str, Any] = {}
    deploy: dict[str, Any] = {}
    env: dict[str, Any] = {}

    # Hints depend on every other collector — force-collect them when hints are
    # requested so the generator never draws conclusions from empty data.
    needs_hints = "hints" in all_sections

    if "services" in all_sections or needs_hints:
        services = collect_services()
    if "services" in all_sections:
        result["services"] = services

    if "git" in all_sections or needs_hints:
        git = collect_git(scan_dirs)
    if "git" in all_sections:
        result["git"] = git

    if "deploy" in all_sections or needs_hints:
        deploy = collect_deploy()
    if "deploy" in all_sections:
        result["deploy"] = deploy

    if "env" in all_sections or needs_hints:
        env = collect_env(extra_env)
    if "env" in all_sections:
        result["env"] = env

    if needs_hints:
        result["hints"] = generate_hints(services, git, deploy, env)

    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="devctx",
        description="Project context snapshot for AI agents",
    )
    parser.add_argument("--version", action="version", version=f"devctx {__version__}")
    parser.add_argument(
        "--services", action="store_true",
        help="Only show running services",
    )
    parser.add_argument(
        "--git", action="store_true",
        help="Only show git state",
    )
    parser.add_argument(
        "--deploy", action="store_true",
        help="Only show deployment state",
    )
    parser.add_argument(
        "--env", action="store_true",
        help="Only show environment health",
    )
    parser.add_argument(
        "--hints", action="store_true",
        help="Only show agent hints",
    )
    parser.add_argument(
        "--scan-dir", action="append", dest="scan_dirs",
        help="Directory to scan for git repos (repeatable; auto-detects repo root or ~)",
    )
    parser.add_argument(
        "--check-env", action="append", dest="extra_env",
        help="Additional env var to check (repeatable)",
    )
    parser.add_argument(
        "--compact", action="store_true",
        help="Compact JSON output (no indentation)",
    )

    args = parser.parse_args()

    # Determine which sections to include
    flags = ["services", "git", "deploy", "env", "hints"]
    selected = [f for f in flags if getattr(args, f, False)]
    sections = selected if selected else None  # None = all

    result = snapshot(
        sections=sections,
        scan_dirs=args.scan_dirs,
        extra_env=args.extra_env,
    )

    indent = None if args.compact else 2
    json.dump(result, sys.stdout, indent=indent, default=str)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
