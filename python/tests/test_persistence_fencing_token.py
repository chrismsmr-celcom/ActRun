"""A stale lease holder must not commit after a newer holder takes over."""

import time

import pytest

from cerbere_cohort import LeaseError
from cerbere_cohort.persistence import PersistentWorkspace


def test_expired_lease_holder_cannot_commit_after_reacquisition(tmp_path):
    db = tmp_path / "fencing-token.db"

    with PersistentWorkspace(db, require_leases=True) as workspace:
        first_lease = workspace.acquire_lease(
            "agent-a",
            "shared/document",
            duration_seconds=0.25,
        )
        stale_branch = workspace.create_branch("agent-a", "agent-a-work")
        stale_branch.set("shared/document", {"value": "stale write"})

    time.sleep(0.4)

    with PersistentWorkspace(db, require_leases=True) as workspace:
        second_lease = workspace.acquire_lease(
            "agent-b",
            "shared/document",
            duration_seconds=30,
        )
        assert second_lease.agent_id == "agent-b"
        assert second_lease.fencing_token > first_lease.fencing_token

    with PersistentWorkspace(db, require_leases=True) as workspace:
        with pytest.raises(LeaseError) as exc_info:
            workspace.commit("agent-a", stale_branch)

        assert exc_info.value.code == "lease_fenced"
        assert workspace.head.data.get("shared/document") is None
