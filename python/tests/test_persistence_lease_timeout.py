"""Verify a timed-out persistent lease waiter releases SQLite promptly."""

import multiprocessing
import sqlite3

from cerbere_cohort import LeaseError
from cerbere_cohort.persistence import PersistentWorkspace


def _wait_until_timeout(db_path, ready, results):
    with PersistentWorkspace(db_path) as workspace:
        ready.set()
        try:
            workspace.acquire_lease(
                "agent-b",
                "resource/timeout",
                duration_seconds=30,
                wait=True,
                timeout_seconds=0.6,
            )
        except LeaseError as exc:
            results.put(("agent-b", "error", exc.code))
        else:
            results.put(("agent-b", "acquired", None))


def test_wait_timeout_does_not_keep_sqlite_write_lock(tmp_path):
    db = tmp_path / "lease-timeout.db"

    with PersistentWorkspace(db) as workspace:
        workspace.acquire_lease(
            "agent-a",
            "resource/timeout",
            duration_seconds=60,
        )

    ctx = multiprocessing.get_context("spawn")
    ready = ctx.Event()
    results = ctx.Queue()
    waiter = ctx.Process(
        target=_wait_until_timeout,
        args=(str(db), ready, results),
    )
    waiter.start()

    assert ready.wait(timeout=10), "waiter did not become ready"
    waiter.join(timeout=10)
    assert not waiter.is_alive(), "waiter did not respect its timeout"
    assert waiter.exitcode == 0

    outcome = results.get(timeout=5)
    assert outcome == ("agent-b", "error", "lease_wait_timeout")

    # The original owner must still be able to release immediately after
    # the other process times out; no SQLite write transaction may remain.
    with PersistentWorkspace(db) as workspace:
        workspace.release_lease("agent-a", "resource/timeout")

    with sqlite3.connect(db) as connection:
        leases = connection.execute(
            "SELECT resource_key, agent_id FROM leases"
        ).fetchall()

    assert leases == []
