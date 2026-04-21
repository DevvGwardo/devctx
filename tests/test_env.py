"""Tests for the env collector."""

import os
from unittest.mock import patch

from devctx.collectors.env import collect_env, EXPECTED_VARS


def test_detects_set_vars():
    with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-xxx"}, clear=False):
        result = collect_env()
        assert "ANTHROPIC_API_KEY" in result["set"]


def test_detects_missing_vars():
    env = {k: "" for k in EXPECTED_VARS}  # all empty → missing
    with patch.dict(os.environ, env, clear=False):
        # Remove them so os.environ.get returns falsy
        for k in EXPECTED_VARS:
            os.environ.pop(k, None)
        result = collect_env()
        for var in EXPECTED_VARS:
            assert var in result["missing"]


def test_extra_vars():
    with patch.dict(os.environ, {"MY_CUSTOM_KEY": "val"}, clear=False):
        result = collect_env(extra_vars=["MY_CUSTOM_KEY"])
        assert "MY_CUSTOM_KEY" in result["set"]


def test_extra_vars_missing():
    os.environ.pop("NONEXISTENT_VAR_12345", None)
    result = collect_env(extra_vars=["NONEXISTENT_VAR_12345"])
    assert "NONEXISTENT_VAR_12345" in result["missing"]


def test_returns_set_and_missing_keys():
    result = collect_env()
    assert "set" in result
    assert "missing" in result
    assert isinstance(result["set"], list)
    assert isinstance(result["missing"], list)
