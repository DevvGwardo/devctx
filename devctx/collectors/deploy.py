"""Collect deployment state from Railway, DigitalOcean, etc."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


def _railway_projects() -> dict[str, Any] | None:
    config_path = Path.home() / ".railway" / "config.json"
    if not config_path.exists():
        return None

    try:
        config = json.loads(config_path.read_text())
        projects = config.get("projects", {})
        project_list = []
        for path, proj in projects.items():
            entry: dict[str, Any] = {"path": path}
            if "name" in proj:
                entry["name"] = proj["name"]
            if "projectId" in proj:
                entry["id"] = proj["projectId"]
            project_list.append(entry)

        result: dict[str, Any] = {"projects": project_list}

        if shutil.which("railway"):
            try:
                r = subprocess.run(
                    ["railway", "status", "--json"],
                    capture_output=True, text=True, timeout=15,
                )
                if r.returncode == 0 and r.stdout.strip():
                    result["current"] = json.loads(r.stdout.strip())
            except (subprocess.TimeoutExpired, json.JSONDecodeError):
                pass

        return result
    except (json.JSONDecodeError, KeyError):
        return None


def _digitalocean_status() -> dict[str, Any] | None:
    if not shutil.which("doctl"):
        return None
    try:
        result = subprocess.run(
            ["doctl", "compute", "droplet", "list", "--format",
             "ID,Name,Status,PublicIPv4,Region", "--no-header"],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode != 0:
            return None

        droplets = []
        for line in result.stdout.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) >= 4:
                droplets.append({
                    "id": parts[0],
                    "name": parts[1],
                    "status": parts[2],
                    "ip": parts[3],
                    "region": parts[4] if len(parts) > 4 else "",
                })
        return {"droplets": droplets} if droplets else None
    except subprocess.TimeoutExpired:
        return None


def collect_deploy() -> dict[str, Any]:
    result: dict[str, Any] = {}

    railway = _railway_projects()
    if railway:
        result["railway"] = railway

    do = _digitalocean_status()
    if do:
        result["digitalocean"] = do

    return result
