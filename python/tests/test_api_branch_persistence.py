import json

from cerbere_cohort import api
from cerbere_cohort.persistence import PersistentWorkspace


def test_api_branch_working_copy_restores_after_registry_reset(tmp_path, monkeypatch):
    store = PersistentWorkspace(tmp_path / "workspace.db")
    store._conn.execute(
        """CREATE TABLE api_branches (
            branch_id TEXT PRIMARY KEY,
            agent_id TEXT NOT NULL,
            branch_name TEXT NOT NULL,
            base_version TEXT NOT NULL,
            current_data_json TEXT NOT NULL,
            intents_json TEXT NOT NULL,
            status TEXT NOT NULL,
            conflicting_keys_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        )"""
    )
    store._conn.commit()
    monkeypatch.setattr(api, "workspace", store)
    monkeypatch.setattr(api, "_branches", {})

    branch = store.create_branch("agent-a", "backend")
    item = {
        "branch": branch,
        "agent_id": "agent-a",
        "status": "open",
        "conflicting_keys": [],
        "created_at": "2026-01-01T00:00:00+00:00",
    }
    branch.set("service.status", "ready", intent="persist this change")
    api._branches["branch-1"] = item
    api._save_api_branch("branch-1", item)

    api._branches.clear()
    api._restore_api_branches()

    restored = api._branches["branch-1"]
    assert restored["branch"].get("service.status") == "ready"
    assert restored["branch"].intents["service.status"] == "persist this change"
    assert restored["status"] == "open"
    store.close()
