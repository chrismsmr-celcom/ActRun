"""Fencing counters must survive lease release and workspace restarts."""

from cerbere_cohort.persistence import PersistentWorkspace


def test_fencing_token_increases_after_release_and_restart(tmp_path):
    db = tmp_path / "fencing-counter.db"

    with PersistentWorkspace(db) as workspace:
        first = workspace.acquire_lease(
            "agent-a",
            "shared/resource",
            duration_seconds=30,
        )
        workspace.release_lease("agent-a", "shared/resource")

    with PersistentWorkspace(db) as workspace:
        second = workspace.acquire_lease(
            "agent-b",
            "shared/resource",
            duration_seconds=30,
        )

    assert first.fencing_token == 1
    assert second.fencing_token == 2
