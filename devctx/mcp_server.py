"""devctx MCP server — expose context snapshot as an MCP tool."""

from __future__ import annotations

import json
import sys

from devctx.cli import snapshot


def handle_request(request: dict) -> dict:
    method = request.get("method", "")
    req_id = request.get("id")

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "devctx", "version": "0.1.0"},
            },
        }

    if method == "notifications/initialized":
        return None  # No response needed for notifications

    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": [
                    {
                        "name": "get_dev_context",
                        "description": (
                            "Returns a structured JSON snapshot of the developer's full environment: "
                            "running services, git repo states, deployment status, env var health, "
                            "and agent-friendly hints. Call this at session start to orient yourself."
                        ),
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "sections": {
                                    "type": "array",
                                    "items": {
                                        "type": "string",
                                        "enum": ["services", "git", "deploy", "env", "hints"],
                                    },
                                    "description": "Which sections to include. Omit for all.",
                                },
                                "scan_dirs": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Directories to scan for git repos.",
                                },
                            },
                        },
                    }
                ]
            },
        }

    if method == "tools/call":
        params = request.get("params", {})
        tool_name = params.get("name", "")

        if tool_name == "get_dev_context":
            arguments = params.get("arguments", {})
            result = snapshot(
                sections=arguments.get("sections"),
                scan_dirs=arguments.get("scan_dirs"),
            )
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {"type": "text", "text": json.dumps(result, indent=2, default=str)}
                    ]
                },
            }

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"},
        }

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Unknown method: {method}"},
    }


def main() -> None:
    """Run as stdio MCP server."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            response = handle_request(request)
            if response is not None:
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()
        except json.JSONDecodeError:
            error = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": "Parse error"},
            }
            sys.stdout.write(json.dumps(error) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
