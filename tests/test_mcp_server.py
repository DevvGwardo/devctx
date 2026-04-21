"""Tests for the MCP server request handler."""

from unittest.mock import patch

from devctx.mcp_server import handle_request


def test_initialize():
    resp = handle_request({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
    assert resp["id"] == 1
    assert resp["result"]["serverInfo"]["name"] == "devctx"
    assert "protocolVersion" in resp["result"]


def test_initialized_notification():
    resp = handle_request({"jsonrpc": "2.0", "method": "notifications/initialized"})
    assert resp is None


def test_tools_list():
    resp = handle_request({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    tools = resp["result"]["tools"]
    assert len(tools) == 1
    assert tools[0]["name"] == "get_dev_context"
    assert "inputSchema" in tools[0]


@patch("devctx.mcp_server.snapshot", return_value={"version": "0.1.0", "timestamp": 0, "env": {"set": [], "missing": []}})
def test_tools_call_get_dev_context(mock_snapshot):
    resp = handle_request({
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {"name": "get_dev_context", "arguments": {"sections": ["env"]}},
    })
    assert resp["id"] == 3
    content = resp["result"]["content"]
    assert len(content) == 1
    assert content[0]["type"] == "text"
    mock_snapshot.assert_called_once_with(sections=["env"], scan_dirs=None)


def test_unknown_tool():
    resp = handle_request({
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {"name": "nonexistent_tool", "arguments": {}},
    })
    assert "error" in resp
    assert resp["error"]["code"] == -32601


def test_unknown_method():
    resp = handle_request({"jsonrpc": "2.0", "id": 5, "method": "foo/bar"})
    assert "error" in resp
    assert resp["error"]["code"] == -32601
