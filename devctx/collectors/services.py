"""Detect running services by scanning ports and processes."""

from __future__ import annotations

import json
import shutil
import socket
import subprocess
from typing import Any

KNOWN_PORTS: dict[int, str] = {
    3000: "dev-server",
    3001: "dev-server-alt",
    3002: "dev-server-alt",
    5001: "flask",
    5173: "vite",
    5432: "postgres",
    5433: "postgres-alt",
    6379: "redis/dragonfly",
    6432: "pgbouncer",
    8080: "http-server",
    8642: "hermes-gateway",
}


def _check_port(port: int, host: str = "127.0.0.1", timeout: float = 0.3) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, ConnectionRefusedError):
        return False


def _get_pid_on_port(port: int) -> int | None:
    try:
        result = subprocess.run(
            ["lsof", "-ti", f":{port}"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return int(result.stdout.strip().split("\n")[0])
    except (subprocess.TimeoutExpired, ValueError):
        pass
    return None


def _get_docker_containers() -> list[dict[str, Any]]:
    if not shutil.which("docker"):
        return []
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{json .}}"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return []
        containers = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            c = json.loads(line)
            containers.append({
                "name": c.get("Names", ""),
                "image": c.get("Image", ""),
                "status": c.get("Status", ""),
                "ports": c.get("Ports", ""),
            })
        return containers
    except (subprocess.TimeoutExpired, json.JSONDecodeError):
        return []


def collect_services() -> dict[str, Any]:
    ports: dict[str, Any] = {}
    for port, label in KNOWN_PORTS.items():
        if _check_port(port):
            entry: dict[str, Any] = {"port": port, "status": "listening", "label": label}
            pid = _get_pid_on_port(port)
            if pid:
                entry["pid"] = pid
            ports[label if list(KNOWN_PORTS.values()).count(label) == 1 else f"{label}:{port}"] = entry

    containers = _get_docker_containers()

    result: dict[str, Any] = {"ports": ports}
    if containers:
        result["docker"] = containers
    return result
