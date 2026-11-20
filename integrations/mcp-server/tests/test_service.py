import pytest

from cerbere_cohort.merge import ConflictError
from cerbere_cohort.lease import LeaseError
from mcp_server import CohortService


def test_branch_state_survives_server_restart(tmp_path):
    db = tmp_path / "cohort.db"
    service = CohortService(db)
    service.create_branch("cursor", "feature")
    service.write_branch("cursor", "feature", "architecture", {"status": "draft"})
    service.close()

    restarted = CohortService(db)
    assert restarted.read_branch("cursor", "feature", "architecture") == {
        "key": "architecture",
        "exists": True,
        "value": {"status": "draft"},
    }
    result = restarted.commit_branch("cursor", "feature")
    assert result["committed"] is True
    assert result["state"]["architecture"] == {"status": "draft"}
    restarted.close()


def test_conflicting_agents_never_silently_overwrite(tmp_path):
    db = tmp_path / "cohort.db"
    service = CohortService(db)
    service.create_branch("cursor", "cursor-work")
    service.create_branch("codex", "codex-work")
    service.write_branch("cursor", "cursor-work", "shared-file", "cursor version")
    service.write_branch("codex", "codex-work", "shared-file", "codex version")

    service.commit_branch("cursor", "cursor-work")
    with pytest.raises(ConflictError):
        service.commit_branch("codex", "codex-work")

    assert service.get_state()["state"]["shared-file"] == "cursor version"
    service.close()


def test_disjoint_agent_changes_merge(tmp_path):
    service = CohortService(tmp_path / "cohort.db")
    service.create_branch("cursor", "a")
    service.create_branch("codex", "b")
    service.write_branch("cursor", "a", "file-a", "A")
    service.write_branch("codex", "b", "file-b", "B")

    service.commit_branch("cursor", "a")
    result = service.commit_branch("codex", "b")
    assert result["state"] == {"file-a": "A", "file-b": "B"}
    service.close()


def test_event_limit_is_validated(tmp_path):
    service = CohortService(tmp_path / "cohort.db")
    with pytest.raises(ValueError):
        service.get_events(0)
    service.close()


def test_bound_mcp_identity_rejects_agent_spoofing(tmp_path):
    service = CohortService(
        tmp_path / "bound.db",
        authenticated_agent_id="agent-a",
    )
    with pytest.raises(ValueError, match="identity bound"):
        service.create_branch("agent-b", "forbidden")
    service.create_branch("agent-a", "allowed")
    service.close()


def test_bound_mcp_identity_filters_events(tmp_path):
    service = CohortService(
        tmp_path / "events.db",
        authenticated_agent_id="agent-a",
    )
    service.create_branch("agent-a", "own")
    service.workspace.create_branch("agent-b", "other")
    events = service.get_events()
    assert events
    assert {event["agent_id"] for event in events} == {"agent-a"}
    service.close()


def test_mcp_branch_fencing_token_survives_restart(tmp_path):
    db = tmp_path / "fencing.db"
    service = CohortService(db, require_leases=True)
    service.create_branch("agent-a", "work")
    lease = service.acquire_lease("agent-a", "record/1", 30)
    assert lease["fencing_token"] >= 1
    service.write_branch("agent-a", "work", "record/1", {"value": 1})
    service.close()

    restarted = CohortService(db, require_leases=True)
    result = restarted.commit_branch("agent-a", "work")
    assert result["committed"] is True
    assert result["state"]["record/1"] == {"value": 1}
    restarted.close()


def test_mcp_rejects_commit_after_lease_takeover(tmp_path):
    service = CohortService(tmp_path / "stale.db", require_leases=True)
    service.create_branch("agent-a", "work")
    service.acquire_lease("agent-a", "record/1", 30)
    service.write_branch("agent-a", "work", "record/1", {"value": "stale"})
    service.workspace.release_lease("agent-a", "record/1")
    service.workspace.acquire_lease("agent-b", "record/1", 30)
    with pytest.raises(LeaseError) as exc:
        service.commit_branch("agent-a", "work")
    assert exc.value.code == "lease_fenced"
    service.close()


def test_mcp_rejects_invalid_lease_duration(tmp_path):
    service = CohortService(tmp_path / "duration.db")
    with pytest.raises(ValueError, match="duration_seconds"):
        service.acquire_lease("agent-a", "record/1", 0)
    service.close()


def test_mcp_agent_scopes_separate_workspace_and_lease_permissions(tmp_path):
    service = CohortService(
        tmp_path / "scopes.db",
        authenticated_agent_id="agent-a",
        agent_scopes=["workspace:read"],
    )
    assert service.get_state()["state"] == {}
    with pytest.raises(Exception) as exc:
        service.create_branch("agent-a", "forbidden")
    assert getattr(exc.value, "code", None) == "insufficient_scope"
    service.close()
