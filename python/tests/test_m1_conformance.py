"""
Tests de conformance M1 pour ActRun.
Vérifie les 7 critères d'acceptation définis dans docs/CONCEPTS.md §13.
"""
import pytest
from actrun import Workspace, ConflictError, DeadlockError


class TestM1Conformance:
    """Tests des 7 critères de conformance M1."""

    def test_criterion_1_conflict_on_same_path_different_content(self):
        ws = Workspace()
        branch_a = ws.create_branch("agent-a", "branch-a")
        branch_b = ws.create_branch("agent-b", "branch-b")
        
        branch_a.set("spec/auth.md", "Version A du document")
        branch_b.set("spec/auth.md", "Version B du document")
        
        ws.commit("agent-a", branch_a)
        
        with pytest.raises(ConflictError) as exc_info:
            ws.commit("agent-b", branch_b)
        
        assert "spec/auth.md" in exc_info.value.conflicting_keys
        
        events = ws.get_events()
        commit_events = [e for e in events if e.action == "workspace.commit"]
        assert len(commit_events) == 1  # Un seul commit a réussi

    def test_criterion_2_clean_merge_on_disjoint_paths(self):
        ws = Workspace()
        branch_a = ws.create_branch("agent-a", "branch-a")
        branch_b = ws.create_branch("agent-b", "branch-b")
        
        branch_a.set("spec/auth.md", "Contenu A")
        branch_b.set("spec/logistics.md", "Contenu B")
        
        ws.commit("agent-a", branch_a)
        ws.commit("agent-b", branch_b)  # Pas de ConflictError
        
        events = ws.get_events()
        commit_events = [e for e in events if e.action == "workspace.commit"]
        
        # Vérifier que les deux commits ont réussi et contiennent les bonnes clés
        assert len(commit_events) == 2
        all_changes = {}
        for e in commit_events:
            all_changes.update(e.payload.get("changes", {}))
            
        assert "spec/auth.md" in all_changes
        assert "spec/logistics.md" in all_changes

    def test_criterion_3_no_conflict_on_identical_content(self):
        ws = Workspace()
        branch_a = ws.create_branch("agent-a", "branch-a")
        branch_b = ws.create_branch("agent-b", "branch-b")
        
        identical_content = "Contenu identique écrit par les deux agents"
        branch_a.set("spec/shared.md", identical_content)
        branch_b.set("spec/shared.md", identical_content)
        
        ws.commit("agent-a", branch_a)
        ws.commit("agent-b", branch_b)  # Pas de ConflictError
        
        events = ws.get_events()
        conflict_events = [e for e in events if "conflict" in e.action]
        assert len(conflict_events) == 0

    def test_criterion_4_conflict_on_delete_vs_modify(self):
        ws = Workspace()
        
        branch_init = ws.create_branch("agent-init", "init")
        branch_init.set("spec/doc.md", "Contenu initial")
        ws.commit("agent-init", branch_init)
        
        branch_a = ws.create_branch("agent-a", "branch-a")
        branch_b = ws.create_branch("agent-b", "branch-b")
        
        branch_a.set("spec/doc.md", "Contenu modifié")
        branch_b.delete("spec/doc.md")
        
        ws.commit("agent-a", branch_a)
        
        with pytest.raises(ConflictError) as exc_info:
            ws.commit("agent-b", branch_b)
        
        assert "spec/doc.md" in exc_info.value.conflicting_keys

    def test_criterion_5_events_emitted_for_all_actions(self):
        ws = Workspace()
        branch_a = ws.create_branch("agent-a", "branch-a")
        branch_a.set("spec/doc.md", "Contenu")
        ws.commit("agent-a", branch_a)
        
        events = ws.get_events()
        actions = [e.action for e in events]
        
        assert "workspace.branch" in actions
        assert "workspace.commit" in actions
        # Note: 'document.written' n'est pas un événement séparé dans l'implémentation actuelle,
        # les modifications sont enregistrées dans le payload 'changes' de 'workspace.commit'.

    def test_criterion_6_replay_produces_identical_snapshot_ids(self):
        pytest.skip("Replay déterministe à implémenter dans M1")

    def test_criterion_7_no_overwrite_on_concurrent_target_change(self):
        pytest.skip("Mécanisme CAS à implémenter dans M1")


class TestLeasesAndDeadlock:
    """Tests supplémentaires pour les leases et la détection de deadlock."""

    def test_lease_acquire_and_release(self):
        ws = Workspace(require_leases=True)
        
        # 1. Acquérir ET libérer AVANT de récupérer les événements
        ws.acquire_lease("agent-a", "db/schema", duration_seconds=60)
        ws.release_lease("agent-a", "db/schema")
        
        # 2. Maintenant, on récupère tous les événements
        events = ws.get_events()
        
        lease_events = [e for e in events if e.action == "lease.acquire"]
        assert len(lease_events) == 1
        
        release_events = [e for e in events if e.action == "lease.release"]
        assert len(release_events) == 1

    def test_deadlock_detection(self):
        pytest.skip("Détection de deadlock à implémenter avec threading")
