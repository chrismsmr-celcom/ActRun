"""A stale lease holder must not commit after a newer holder takes over."""

import time

import pytest

from cerbere_cohort import CallbackResolver, LeaseError, Resolution, Workspace
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

def test_fencing_is_revalidated_after_slow_conflict_resolver():
    workspace = Workspace(require_leases=True)
    workspace.seed({"shared/document": "base"})

    first_lease = workspace.acquire_lease("agent-a", "shared/document", duration_seconds=30)
    stale_branch = workspace.create_branch("agent-a", "agent-a-work")
    stale_branch.set("shared/document", "agent-a proposal")
    workspace.seed({"shared/document": "concurrent update"})

    def take_over_during_resolution(conflict):
        workspace.release_lease("agent-a", "shared/document")
        replacement = workspace.acquire_lease("agent-b", "shared/document", duration_seconds=30)
        assert replacement.fencing_token > first_lease.fencing_token
        return Resolution.with_value("resolver output")

    resolver = CallbackResolver(take_over_during_resolution, name="takeover-test")
    with pytest.raises(LeaseError) as exc_info:
        workspace.commit("agent-a", stale_branch, resolver=resolver)

    assert exc_info.value.code == "lease_fenced"
    assert workspace.head.data["shared/document"] == "concurrent update"

def test_lease_cannot_be_reacquired_between_final_validation_and_commit():
    import threading

    workspace = Workspace(require_leases=True)
    workspace.seed({"shared/document": "base"})
    workspace.acquire_lease("agent-a", "shared/document", duration_seconds=30)
    branch = workspace.create_branch("agent-a", "agent-a-work")
    branch.set("shared/document", "agent-a write")
    workspace.seed({"shared/document": "concurrent update"})

    final_validation_entered = threading.Event()
    allow_finalization = threading.Event()
    takeover_acquired = threading.Event()
    original_validate = workspace._validate_branch_leases
    validation_count = 0
    count_lock = threading.Lock()

    def pause_on_final_validation(agent_id, target_branch, base):
        nonlocal validation_count
        with count_lock:
            validation_count += 1
            current = validation_count
        if current == 2:
            final_validation_entered.set()
            assert allow_finalization.wait(timeout=5), "test did not release finalization"
        return original_validate(agent_id, target_branch, base)

    workspace._validate_branch_leases = pause_on_final_validation

    commit_errors = []

    def commit():
        try:
            resolver = CallbackResolver(
                lambda conflict: Resolution.with_value("resolved write"),
                name="test-resolver",
            )
            workspace.commit("agent-a", branch, resolver=resolver)
        except Exception as exc:  # noqa: BLE001
            commit_errors.append(exc)

    def take_over():
        workspace.acquire_lease("agent-b", "shared/document", duration_seconds=30)
        takeover_acquired.set()

    commit_thread = threading.Thread(target=commit)
    commit_thread.start()
    assert final_validation_entered.wait(timeout=5), "commit did not reach final validation"

    takeover_thread = threading.Thread(target=take_over)
    takeover_thread.start()
    assert not takeover_acquired.wait(timeout=0.1), (
        "lease takeover must wait until the fenced commit is finalized"
    )

    allow_finalization.set()
    commit_thread.join(timeout=5)
    takeover_thread.join(timeout=5)

    assert not commit_thread.is_alive()
    assert not takeover_thread.is_alive()
    assert commit_errors == []
    assert takeover_acquired.is_set()
    assert workspace.head.data["shared/document"] == "resolved write"
    assert workspace._lease_manager.get_active_leases()["shared/document"].agent_id == "agent-b"

