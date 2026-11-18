"""Regression tests for lease exclusivity across independent OS processes."""

import multiprocessing
import sqlite3

from cerbere_cohort import LeaseError
from cerbere_cohort.persistence import PersistentWorkspace


def _acquire_from_process(db_path, agent_id, barrier, results):
    with PersistentWorkspace(db_path) as workspace:
        # Both processes have opened their own connection before racing.
        barrier.wait(timeout=15)
        try:
            workspace.acquire_lease(
                agent_id,
                "resource/shared",
                duration_seconds=60,
            )
        except LeaseError:
            results.put((agent_id, "held"))
        else:
            results.put((agent_id, "acquired"))


def test_two_processes_cannot_acquire_the_same_lease(tmp_path):
    db = tmp_path / "multi-process-lease.db"
    with PersistentWorkspace(db):
        pass

    ctx = multiprocessing.get_context("spawn")
    barrier = ctx.Barrier(2)
    results = ctx.Queue()
    workers = [
        ctx.Process(
            target=_acquire_from_process,
            args=(str(db), agent_id, barrier, results),
        )
        for agent_id in ("agent-a", "agent-b")
    ]

    for worker in workers:
        worker.start()

    for worker in workers:
        worker.join(timeout=30)

    for worker in workers:
        assert not worker.is_alive(), "lease worker did not finish"
        assert worker.exitcode == 0

    outcomes = sorted(results.get(timeout=5) for _ in workers)
    assert sorted(status for _, status in outcomes) == ["acquired", "held"]

    # Verify the persisted source of truth, not only either process's memory.
    with sqlite3.connect(db) as connection:
        leases = connection.execute(
            "SELECT resource_key, agent_id FROM leases"
        ).fetchall()
        acquire_events = connection.execute(
            "SELECT COUNT(*) FROM events WHERE action = 'lease.acquire'"
        ).fetchone()[0]

    assert len(leases) == 1
    assert leases[0][0] == "resource/shared"
    assert leases[0][1] in {"agent-a", "agent-b"}
    assert acquire_events == 1
