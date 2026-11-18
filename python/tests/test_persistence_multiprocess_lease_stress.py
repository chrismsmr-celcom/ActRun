"""Stress the persisted lease lock with ten independent processes."""

import multiprocessing
import sqlite3

from cerbere_cohort import LeaseError
from cerbere_cohort.persistence import PersistentWorkspace


def _race_for_one_resource(db_path, agent_id, barrier, results):
    with PersistentWorkspace(db_path) as workspace:
        barrier.wait(timeout=20)
        try:
            workspace.acquire_lease(agent_id, "resource/contended", duration_seconds=120)
        except LeaseError:
            results.put((agent_id, "held"))
        else:
            results.put((agent_id, "acquired"))


def test_ten_processes_produce_exactly_one_active_lease(tmp_path):
    db = tmp_path / "ten-process-leases.db"
    with PersistentWorkspace(db):
        pass

    ctx = multiprocessing.get_context("spawn")
    count = 10
    barrier = ctx.Barrier(count)
    results = ctx.Queue()
    workers = [
        ctx.Process(
            target=_race_for_one_resource,
            args=(str(db), f"agent-{index}", barrier, results),
        )
        for index in range(count)
    ]

    for worker in workers:
        worker.start()

    for worker in workers:
        worker.join(timeout=45)

    for worker in workers:
        assert not worker.is_alive(), "lease worker did not finish"
        assert worker.exitcode == 0

    outcomes = [results.get(timeout=5) for _ in workers]
    assert sum(status == "acquired" for _, status in outcomes) == 1
    assert sum(status == "held" for _, status in outcomes) == count - 1

    with sqlite3.connect(db) as connection:
        leases = connection.execute(
            "SELECT resource_key, agent_id FROM leases"
        ).fetchall()
        acquire_events = connection.execute(
            "SELECT COUNT(*) FROM events WHERE action = 'lease.acquire'"
        ).fetchone()[0]

    assert leases == [("resource/contended", next(
        agent for agent, status in outcomes if status == "acquired"
    ))]
    assert acquire_events == 1
