"""Verify that another process can acquire a lease after expiry."""

import sqlite3
import time

from cerbere_cohort.persistence import PersistentWorkspace


def test_expired_persisted_lease_can_be_reacquired_by_another_process(tmp_path):
    db = tmp_path / "expired-lease.db"

    with PersistentWorkspace(db) as workspace:
        first = workspace.acquire_lease(
            "agent-a",
            "resource/expiring",
            duration_seconds=0.25,
        )
        assert first.agent_id == "agent-a"

    time.sleep(0.4)

    with PersistentWorkspace(db) as workspace:
        second = workspace.acquire_lease(
            "agent-b",
            "resource/expiring",
            duration_seconds=30,
        )
        assert second.agent_id == "agent-b"

    with sqlite3.connect(db) as connection:
        leases = connection.execute(
            "SELECT resource_key, agent_id FROM leases"
        ).fetchall()
        acquire_events = connection.execute(
            "SELECT COUNT(*) FROM events WHERE action = 'lease.acquire'"
        ).fetchone()[0]

    assert leases == [("resource/expiring", "agent-b")]
    assert acquire_events == 2
