#!/usr/bin/env python3
"""Archive GitHub repository traffic snapshots (clones and views)."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPOSITORY = "chrismsmr-celcom/cerbere-cohort"
OUTPUT = Path("metrics/github-traffic.json")



def github_get(endpoint: str, token: str) -> dict:
    request = urllib.request.Request(
        f"https://api.github.com/repos/{REPOSITORY}/traffic/{endpoint}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "cohort-traffic-archive",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        print(f"GitHub API error: HTTP {error.code}")
        print(f"Response: {details}")
        print(f"Rate limit remaining: {error.headers.get('X-RateLimit-Remaining')}")
        print(f"Required permissions: {error.headers.get('X-Accepted-GitHub-Permissions')}")
        raise



def main() -> None:
    token = os.environ.get("COHORT_TRAFFIC_TOKEN", "").strip()
    if not token:
        raise SystemExit("Missing COHORT_TRAFFIC_TOKEN secret (repository traffic read access required).")

    clones = github_get("clones", token)
    views = github_get("views", token)
    today = datetime.now(timezone.utc).date().isoformat()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    try:
        history = json.loads(OUTPUT.read_text(encoding="utf-8"))
    except FileNotFoundError:
        history = {"repository": REPOSITORY, "snapshots": []}

    row = {
        "date": today,
        "clones": int(clones.get("count", 0)),
        "unique_cloners": int(clones.get("uniques", 0)),
        "views": int(views.get("count", 0)),
        "unique_visitors": int(views.get("uniques", 0)),
    }
    snapshots = [item for item in history.get("snapshots", []) if item.get("date") != today]
    snapshots.append(row)
    snapshots.sort(key=lambda item: item["date"])
    history = {
        "repository": REPOSITORY,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source_window_days": 14,
        "snapshots": snapshots,
    }
    OUTPUT.write_text(json.dumps(history, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(row))


if __name__ == "__main__":
    main()
