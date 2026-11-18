"""Verify a waiting process does not prevent another process releasing a lease."""

import multiprocessing

from cerbere_cohort import LeaseError
from cerbere_cohort.persistence import PersistentWorkspace


def _wait_for_lease(db_path, ready, results):
    with PersistentWorkspace(db_path) as workspace:
        ready.set()
        try:
            lease = workspace.acquire_lease(
                "agent-b",
                "resource/handoff",
                duration_seconds=30,
                wait=True,
                timeout_seconds=4,
            )
        except LeaseError as exc:
            results.put(("agent-b", "timeout", exc.code))
        else:
            results.put(("agent-b", "acquired", lease.agent_id))


def test_waiting_process_gets_lease_after_other_process_releases(tmp_path):
    db = tmp_path / "lease-handoff.db"
    with PersistentWorkspace(db) as workspace:
        workspace.acquire_lease("agent-a", "resource/handoff", duration_seconds=60)

    ctx = multiprocessing.get_context("spawn")
    ready = ctx.Event()
    results = ctx.Queue()
    waiter = ctx.Process(target=_wait_for_lease, args=(str(db), ready, results))
    waiter.start()

    assert ready.wait(timeout=10), "waiter did not become ready"

    # Give the waiter time to enter acquire_lease before releasing from
    # an independent SQLite connection.
    import time
    time.sleep(0.5)

    with PersistentWorkspace(db) as workspace:
        workspace.release_lease("agent-a", "resource/handoff")

    waiter.join(timeout=15)
    assert not waiter.is_alive(), "waiter did not finish"
    assert waiter.exitcode == 0

    outcome = results.get(timeout=5)
    assert outcome == ("agent-b", "acquired", "agent-b")

    with PersistentWorkspace(db) as workspace:
        leases = workspace._conn.execute(
            "SELECT resource_key, agent_id FROM leases"
        ).fetchall()
        assert [(row["resource_key"], row["agent_id"]) for row in leases] == [
            ("resource/handoff", "agent-b")
        ]
