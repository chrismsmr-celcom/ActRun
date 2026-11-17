import pytest

from cerbere_cohort.merge import ConflictError
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
