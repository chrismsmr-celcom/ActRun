"""Concurrency regression tests for atomic lease fencing."""

import threading
import time

from cerbere_cohort import Workspace


def test_lease_takeover_cannot_interleave_between_validation_and_finalize(monkeypatch):
    workspace = Workspace(require_leases=True)
    workspace.seed({"shared/document": "base"})
    first = workspace.acquire_lease("agent-a", "shared/document", duration_seconds=30)
    branch = workspace.create_branch("agent-a", "agent-a-work")
    branch.set("shared/document", "agent-a update")

    finalize_entered = threading.Event()
    allow_finalize = threading.Event()
    takeover_started = threading.Event()
    takeover_finished = threading.Event()
    original_finalize = workspace._finalize

    def paused_finalize(*args, **kwargs):
        finalize_entered.set()
        assert allow_finalize.wait(timeout=2), "test did not release finalize"
        return original_finalize(*args, **kwargs)

    monkeypatch.setattr(workspace, "_finalize", paused_finalize)

    commit_errors = []

    def commit():
        try:
            workspace.commit("agent-a", branch)
        except Exception as exc:  # pragma: no cover - asserted below
            commit_errors.append(exc)

    def takeover():
        takeover_started.set()
        workspace.release_lease("agent-a", "shared/document")
        replacement = workspace.acquire_lease(
            "agent-b", "shared/document", duration_seconds=30
        )
        assert replacement.fencing_token > first.fencing_token
        takeover_finished.set()

    commit_thread = threading.Thread(target=commit)
    commit_thread.start()
    assert finalize_entered.wait(timeout=2), "commit never reached finalize"

    takeover_thread = threading.Thread(target=takeover)
    takeover_thread.start()
    assert takeover_started.wait(timeout=2), "takeover thread never started"
    time.sleep(0.05)

    # Ownership must remain stable until the validated commit has finalized.
    assert not takeover_finished.is_set()

    allow_finalize.set()
    commit_thread.join(timeout=2)
    takeover_thread.join(timeout=2)

    assert not commit_thread.is_alive()
    assert not takeover_thread.is_alive()
    assert not commit_errors
    assert takeover_finished.is_set()
    assert workspace.head.data["shared/document"] == "agent-a update"
