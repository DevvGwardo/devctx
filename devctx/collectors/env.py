"""Check environment variable health — presence only, never values."""

from __future__ import annotations

import os
from typing import Any

EXPECTED_VARS: list[str] = [
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "DO_API_TOKEN",
    "RAILWAY_TOKEN",
    "CF_API_TOKEN",
    "GITHUB_TOKEN",
    "NOUS_API_KEY",
]


def collect_env(extra_vars: list[str] | None = None) -> dict[str, Any]:
    check_vars = EXPECTED_VARS + (extra_vars or [])
    present = []
    missing = []

    for var in check_vars:
        if os.environ.get(var):
            present.append(var)
        else:
            missing.append(var)

    return {
        "set": present,
        "missing": missing,
    }
