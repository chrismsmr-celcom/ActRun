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


def test_branch_diff_preview_reports_proposed_and_concurrent_values(tmp_path, monkeypatch):
    store = PersistentWorkspace(tmp_path / "diff.db")
    store.seed({"profile/name": "Initial", "profile/role": "writer"})
    target = store.create_branch("agent-a", "profile-update")
    concurrent = store.create_branch("agent-b", "role-update")

    target.set("profile/name", "Alice", intent="Update the display name")
    target.set("profile/role", "admin")
    concurrent.set("profile/name", "Bob")
    store.commit("agent-b", concurrent)

    monkeypatch.setattr(api, "workspace", store)
    monkeypatch.setattr(api, "_branches", {
        "target-branch": {
            "branch": target,
            "agent_id": "agent-a",
            "status": "open",
            "conflicting_keys": ["profile/name"],
            "created_at": "2026-01-01T00:00:00+00:00",
        }
    })

    result = api.get_branch_diff("target-branch", context={"principal_type": "user"})

    assert result["change_count"] == 2
    name_change = next(change for change in result["changes"] if change["key"] == "profile/name")
    assert name_change["base"] == "Initial"
    assert name_change["proposed"] == "Alice"
    assert name_change["head"] == "Bob"
    assert name_change["head_changed_since_base"] is True
    assert name_change["intent"] == "Update the display name"

    role_change = next(change for change in result["changes"] if change["key"] == "profile/role")
    assert role_change["base"] == "writer"
    assert role_change["proposed"] == "admin"
    assert role_change["head_changed_since_base"] is False
    store.close()
