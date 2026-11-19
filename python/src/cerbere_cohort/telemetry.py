"""Opt-in, privacy-minimal self-hosted installation telemetry.

No project data, agent names, prompts, workspace contents, credentials, or host
identifiers are collected. Telemetry is disabled unless explicitly enabled.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from uuid import UUID, uuid4

from . import __version__


def _enabled() -> bool:
    return os.getenv("COHORT_TELEMETRY", "false").lower() in {"1", "true", "yes", "on"}


def _installation_id() -> str:
    configured = os.getenv("COHORT_TELEMETRY_ID_PATH", "").strip()
    path = Path(configured).expanduser() if configured else Path.home() / ".config" / "cerbere-cohort" / "telemetry-id"
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        value = path.read_text(encoding="utf-8").strip()
        return str(UUID(value))
    except (FileNotFoundError, ValueError):
        value = str(uuid4())
        try:
            with path.open("x", encoding="utf-8") as handle:
                handle.write(value)
        except FileExistsError:
            return str(UUID(path.read_text(encoding="utf-8").strip()))
        return value


def send_installation_ping() -> bool:
    """Send one best-effort heartbeat; never block startup or fail the service."""
    if not _enabled():
        return False
    endpoint = os.getenv("COHORT_TELEMETRY_URL", "").strip()
    if not endpoint.startswith(("https://", "http://")):
        return False
    payload = {
        "installation_id": _installation_id(),
        "version": __version__,
        "deployment_type": "self-hosted",
    }
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "Cohort-Opt-In-Telemetry"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=2) as response:
            return 200 <= response.status < 300
    except (OSError, urllib.error.URLError, TimeoutError, ValueError):
        return False
