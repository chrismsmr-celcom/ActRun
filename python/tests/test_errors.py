# python/tests/test_errors.py
"""Contrat d'erreurs structuré : codes stables, détails machine, messages français préservés."""
import time

import pytest

from cerbere_cohort import (
    CerbereError,
    ContentError,
    ConflictError,
    DeadlockError,
    LeaseError,
    ResolutionError,
    ReplayError,
)
from cerbere_cohort.errors import CerbereError as CerbereErrorDirect
from cerbere_cohort.merge import ConflictError as ConflictErrorDirect
from cerbere_cohort.resolve import CallbackResolver, Resolution, Resolver
from cerbere_cohort.workspace import Workspace


def _seeded_workspace():
    ws = Workspace()
    ws.seed({"spec/auth": "initial"})
    return ws


class TestConflictCodes:
    def test_conflict_detected_code_and_details(self):
        ws = _seeded_workspace()
        a = ws.create_branch("agent-a", "draft-a")
        b = ws.create_branch("agent-b", "draft-b")
        a.set("spec/auth", "version A")
        b.set("spec/auth", "version B")
        ws.commit("agent-a", a)
        base_version = b.base_version
        with pytest.raises(ConflictError) as info:
            ws.commit("agent-b", b)
        exc = info.value
        assert exc.code == "conflict_detected"
        assert exc.conflicting_keys == ["spec/auth"]
        assert exc.details["conflicting_keys"] == ["spec/auth"]
        assert exc.details["base_version"] == base_version
        assert "head_version" in exc.details and exc.details["head_version"]
        assert "Conflit détecté" in str(exc)  # message français préservé
        assert isinstance(exc, CerbereError)
        envelope = exc.to_dict()
        assert envelope["code"] == "conflict_detected"
        assert envelope["details"]["conflicting_keys"] == ["spec/auth"]

    def test_delete_versus_modify_is_a_conflict_with_details(self):
        ws = _seeded_workspace()
        a = ws.create_branch("agent-a", "draft-a")
        b = ws.create_branch("agent-b", "draft-b")
        a.delete("spec/auth")
        b.set("spec/auth", "version B")
        ws.commit("agent-a", a)
        with pytest.raises(ConflictError) as info:
            ws.commit("agent-b", b)
        assert info.value.code == "conflict_detected"
        assert info.value.details["conflicting_keys"] == ["spec/auth"]


class _HeadMover(Resolver):
    """Résolveur qui déplace HEAD par un commit tiers pendant sa décision."""

    name = "head-mover"

    def __init__(self, ws: Workspace):
        self._ws = ws

    def resolve(self, conflict):
        other = self._ws.create_branch("agent-c", "draft-c")
        other.set("autre/clé", f"tour-{len(self._ws.get_events())}")
        self._ws.commit("agent-c", other)
        return Resolution.take(conflict.ours)


class TestResolverPaths:
    def test_unresolved_conflict_code(self):
        class Refuse(Resolver):
            name = "refuse"

            def resolve(self, conflict):
                return None

        ws = _seeded_workspace()
        a = ws.create_branch("agent-a", "draft-a")
        b = ws.create_branch("agent-b", "draft-b")
        a.set("spec/auth", "version A")
        b.set("spec/auth", "version B")
        ws.commit("agent-a", a)
        with pytest.raises(ConflictError) as info:
            ws.commit("agent-b", b, resolver=Refuse())
        assert info.value.code == "conflict_unresolved"
        assert info.value.details["resolver"] == "refuse"
        assert info.value.conflicting_keys == ["spec/auth"]

    def test_resolver_failure_keeps_cause_in_details_not_only_repr(self):
        class Boom(Resolver):
            name = "boom"

            def resolve(self, conflict):
                raise RuntimeError("panne interne")

        ws = _seeded_workspace()
        b = ws.create_branch("agent-b", "draft-b")
        a = ws.create_branch("agent-a", "draft-a")
        a.set("spec/auth", "version A")
        b.set("spec/auth", "version B")
        ws.commit("agent-a", a)
        with pytest.raises(ResolutionError) as info:
            ws.commit("agent-b", b, resolver=Boom())
        assert info.value.code == "resolution_error"
        assert info.value.details["resolver"] == "boom"
        assert "panne interne" in info.value.details["cause"]
        assert "résolveur 'boom' en échec sur 'spec/auth'" in str(info.value)

    def test_head_kept_moving_code(self):
        ws = _seeded_workspace()
        b = ws.create_branch("agent-b", "draft-b")
        a = ws.create_branch("agent-a", "draft-a")
        a.set("spec/auth", "version A")
        b.set("spec/auth", "version B")
        ws.commit("agent-a", a)
        with pytest.raises(ConflictError) as info:
            ws.commit("agent-b", b, resolver=_HeadMover(ws))
        assert info.value.code == "conflict_head_moved"
        assert info.value.details["attempts"] == 4  # max_retries (3) + 1


class TestLeaseCodes:
    def test_lease_held_code_with_details(self):
        ws = Workspace()
        ws.acquire_lease("agent-a", "res/x", duration_seconds=30)
        with pytest.raises(LeaseError) as info:
            ws.acquire_lease("agent-b", "res/x", duration_seconds=30)
        exc = info.value
        assert exc.code == "lease_held"
        assert exc.details["resource_key"] == "res/x"
        assert exc.details["holder"] == "agent-a"
        assert exc.details["expires_at"] > time.time()
        assert "déjà verrouillée par 'agent-a'" in str(exc)

    def test_lease_wait_timeout_code(self):
        ws = Workspace()
        ws.acquire_lease("agent-a", "res/y", duration_seconds=30)
        with pytest.raises(LeaseError) as info:
            ws.acquire_lease("agent-b", "res/y", duration_seconds=30,
                             wait=True, timeout_seconds=0.05)
        assert info.value.code == "lease_wait_timeout"
        assert info.value.details["holder"] == "agent-a"
        assert info.value.details["timeout_seconds"] == 0.05

    def test_lease_deadlock_code_with_cycle_details(self):
        import threading

        lm_ws = Workspace()
        lm_ws.acquire_lease("agent-a", "res/a2", 60)
        lm_ws.acquire_lease("agent-b", "res/b2", 60)

        def a_waits_for_b():
            lm_ws.acquire_lease("agent-a", "res/b2", wait=True, timeout_seconds=3)

        th = threading.Thread(target=a_waits_for_b)
        th.start()
        time.sleep(0.2)
        with pytest.raises(DeadlockError) as info:
            lm_ws.acquire_lease("agent-b", "res/a2", wait=True, timeout_seconds=3)
        th.join(timeout=5)
        assert info.value.code == "lease_deadlock"
        cycle = info.value.details["cycle"]
        resources = info.value.details["resources"]
        assert len(cycle) == len(resources) == 2
        assert sorted(cycle) == ["agent-a", "agent-b"]

    def test_lease_not_owner_code_with_holder_details(self):
        ws = Workspace()
        ws.acquire_lease("agent-a", "res/c", duration_seconds=30)
        with pytest.raises(LeaseError) as info:
            ws.release_lease("agent-b", "res/c")
        exc = info.value
        assert exc.code == "lease_not_owner"
        assert exc.details == {
            "agent_id": "agent-b",
            "resource_key": "res/c",
            "holder": "agent-a",
        }
        assert "ne peut pas libérer le verrou" in str(exc)

    def test_lease_required_code_on_unleased_write(self):
        ws = Workspace(require_leases=True)
        branch = ws.create_branch("agent-a", "draft-a")
        with pytest.raises(LeaseError) as info:
            branch.set("spec/x", 1)
        assert info.value.code == "lease_required"
        assert info.value.details["key"] == "spec/x"
        assert info.value.details["agent_id"] == "agent-a"


class TestOtherDomainCodes:
    def test_content_error_code_and_isinstance_valueerror(self):
        with pytest.raises(ContentError) as info:
            from cerbere_cohort.hashing import canonical_json
            canonical_json({1: "clé non str"})
        assert info.value.code == "content_invalid_value"
        assert isinstance(info.value, ValueError)  # compat historique
        assert isinstance(info.value, CerbereError)

    def test_corrupted_object_replay_error_details(self):
        from cerbere_cohort.workspace import ContentStore
        store = ContentStore()
        digest = store.put({"a": 1})
        with pytest.raises(ReplayError) as info:
            store.load_text(digest, "actrun.snapshot.v1\n{\"contenu\": mensonge}")
        assert info.value.code == "replay_error"
        assert info.value.details["digest"] == digest

    def test_cerbere_error_is_exception(self):
        assert issubclass(CerbereError, Exception)

    def test_direct_import_matches_package_export(self):
        assert CerbereErrorDirect is CerbereError
        assert ConflictErrorDirect is ConflictError


class TestBackwardCompatibility:
    def test_conflict_error_positional_construction(self):
        exc = ConflictError("message", ["k1", "k2"])
        assert exc.conflicting_keys == ["k1", "k2"]
        assert exc.details["conflicting_keys"] == ["k1", "k2"]
        assert exc.code == "conflict_detected"

    def test_lease_error_plain_construction(self):
        exc = LeaseError("ancien message")
        assert exc.code == "lease_error"
        assert exc.details == {}

    def test_conflicting_keys_attribute_still_available(self):
        """Les tests existants attrapent ConflictError et lisent .conflicting_keys."""
        ws = _seeded_workspace()
        a = ws.create_branch("agent-a", "draft-a")
        b = ws.create_branch("agent-b", "draft-b")
        a.set("spec/auth", "version A")
        b.set("spec/auth", "version B")
        ws.commit("agent-a", a)
        with pytest.raises(ConflictError) as info:
            ws.commit("agent-b", b)
        assert info.value.conflicting_keys == ["spec/auth"]
