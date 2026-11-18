"""Regression tests for SQLite commits from independent OS processes."""

import multiprocessing

from cerbere_cohort import ConflictError
from cerbere_cohort.persistence import PersistentWorkspace


def _commit_from_process(db_path, agent_id, key, value, barrier, results):
    with PersistentWorkspace(db_path) as workspace:
        branch = workspace.create_branch(agent_id, agent_id)
        branch.set(key, value)
        # Both processes must hold branches based on the same persisted HEAD.
        barrier.wait(timeout=15)
        try:
            workspace.commit(agent_id, branch)
        except ConflictError:
            results.put((agent_id, "conflict"))
        else:
            results.put((agent_id, "committed"))


def _run_workers(db_path, writes):
    ctx = multiprocessing.get_context("spawn")
    barrier = ctx.Barrier(len(writes))
    results = ctx.Queue()
    workers = [
        ctx.Process(
            target=_commit_from_process,
            args=(str(db_path), agent_id, key, value, barrier, results),
        )
        for agent_id, key, value in writes
    ]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(timeout=30)
    for worker in workers:
        assert not worker.is_alive(), "worker did not finish"
        assert worker.exitcode == 0
    return sorted(results.get(timeout=5) for _ in workers)


def test_concurrent_disjoint_commits_are_merged_without_lost_updates(tmp_path):
    db = tmp_path / "multi-process-disjoint.db"
    with PersistentWorkspace(db) as workspace:
        workspace.seed({"initial": True})

    outcomes = _run_workers(
        db,
        [("agent-a", "result/a", 1), ("agent-b", "result/b", 2)],
    )
    assert outcomes == [("agent-a", "committed"), ("agent-b", "committed")]

    with PersistentWorkspace(db) as workspace:
        assert workspace.head.data == {"initial": True, "result/a": 1, "result/b": 2}


def test_concurrent_conflicting_commits_reject_exactly_one_writer(tmp_path):
    db = tmp_path / "multi-process-conflict.db"
    with PersistentWorkspace(db) as workspace:
        workspace.seed({"shared": "initial"})

    outcomes = _run_workers(
        db,
        [("agent-a", "shared", "from-a"), ("agent-b", "shared", "from-b")],
    )
    assert sorted(result for _, result in outcomes) == ["committed", "conflict"]

    with PersistentWorkspace(db) as workspace:
        assert workspace.head.data["shared"] in {"from-a", "from-b"}
        actions = [event.action for event in workspace.get_events()]
        assert actions.count("workspace.commit") == 2  # seed + exactly one writer
        assert actions.count("coordination.conflict") == 1
