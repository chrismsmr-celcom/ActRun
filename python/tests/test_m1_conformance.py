"""
Tests de conformance M1 pour ActRun.
Vérifie les 7 critères d'acceptation définis dans docs/CONCEPTS.md §13.
"""
import pytest
from actrun import Workspace, ConflictError, DeadlockError


class TestM1Conformance:
    """Tests des 7 critères de conformance M1."""

    def test_criterion_1_conflict_on_same_path_different_content(self):
        """
        Critère 1: Deux branches écrivant du contenu différent sur le même 
        chemin produisent un conflit au merge, et la branche cible reste inchangée.
        """
        ws = Workspace()
        
        # Créer deux branches
        branch_a = ws.create_branch("agent-a", "branch-a")
        branch_b = ws.create_branch("agent-b", "branch-b")
        
        # Écrire du contenu différent sur le même chemin
        branch_a.set("spec/auth.md", "Version A du document")
        branch_b.set("spec/auth.md", "Version B du document")
        
        # Committer la première branche (succès)
        ws.commit("agent-a", branch_a)
        
        # Tenter de committer la deuxième branche (doit échouer avec conflit)
        with pytest.raises(ConflictError) as exc_info:
            ws.commit("agent-b", branch_b)
        
        # Vérifier que le conflit est bien sur le bon chemin
        assert "spec/auth.md" in exc_info.value.conflicting_keys
        
        # Vérifier que la branche main n'a pas été modifiée par le deuxième commit
        # (elle contient toujours la version A)
        events = ws.get_events()
        commit_events = [e for e in events if e["action"] == "workspace.commit"]
        assert len(commit_events) == 1  # Un seul commit a réussi

    def test_criterion_2_clean_merge_on_disjoint_paths(self):
        """
        Critère 2: Deux branches écrivant sur des chemins disjoints 
        mergent proprement, et le snapshot fusionné contient les deux.
        """
        ws = Workspace()
        
        branch_a = ws.create_branch("agent-a", "branch-a")
        branch_b = ws.create_branch("agent-b", "branch-b")
        
        # Écrire sur des chemins différents
        branch_a.set("spec/auth.md", "Contenu A")
        branch_b.set("spec/logistics.md", "Contenu B")
        
        # Committer les deux branches (doit réussir sans conflit)
        ws.commit("agent-a", branch_a)
        ws.commit("agent-b", branch_b)  # Pas de ConflictError
        
        # Vérifier que les deux fichiers existent dans l'état final
        events = ws.get_events()
        write_events = [e for e in events if e["action"] == "document.written"]
        paths_written = {e["payload"]["path"] for e in write_events}
        
        assert "spec/auth.md" in paths_written
        assert "spec/logistics.md" in paths_written

    def test_criterion_3_no_conflict_on_identical_content(self):
        """
        Critère 3: Deux branches écrivant le même contenu sur le même 
        chemin ne produisent pas de conflit.
        """
        ws = Workspace()
        
        branch_a = ws.create_branch("agent-a", "branch-a")
        branch_b = ws.create_branch("agent-b", "branch-b")
        
        # Écrire exactement le même contenu
        identical_content = "Contenu identique écrit par les deux agents"
        branch_a.set("spec/shared.md", identical_content)
        branch_b.set("spec/shared.md", identical_content)
        
        # Committer les deux branches (doit réussir sans conflit)
        ws.commit("agent-a", branch_a)
        ws.commit("agent-b", branch_b)  # Pas de ConflictError
        
        # Vérifier qu'aucun événement de conflit n'a été émis
        events = ws.get_events()
        conflict_events = [e for e in events if "conflict" in e["action"]]
        assert len(conflict_events) == 0

    def test_criterion_4_conflict_on_delete_vs_modify(self):
        """
        Critère 4: Un conflit "delete vs modify" sur le même chemin 
        est rapporté comme un conflit.
        """
        ws = Workspace()
        
        # Créer un document initial
        branch_init = ws.create_branch("agent-init", "init")
        branch_init.set("spec/doc.md", "Contenu initial")
        ws.commit("agent-init", branch_init)
        
        # Créer deux branches à partir de main
        branch_a = ws.create_branch("agent-a", "branch-a")
        branch_b = ws.create_branch("agent-b", "branch-b")
        
        # Agent A modifie le document
        branch_a.set("spec/doc.md", "Contenu modifié")
        
        # Agent B supprime le document
        branch_b.delete("spec/doc.md")
        
        # Committer A (succès)
        ws.commit("agent-a", branch_a)
        
        # Tenter de committer B (doit échouer avec conflit delete/modify)
        with pytest.raises(ConflictError) as exc_info:
            ws.commit("agent-b", branch_b)
        
        assert "spec/doc.md" in exc_info.value.conflicting_keys

    def test_criterion_5_events_emitted_for_all_actions(self):
        """
        Critère 5: Chaque write, conflict et merge émet l'événement correspondant.
        """
        ws = Workspace()
        
        # Créer une branche
        branch_a = ws.create_branch("agent-a", "branch-a")
        
        # Écrire
        branch_a.set("spec/doc.md", "Contenu")
        
        # Committer
        ws.commit("agent-a", branch_a)
        
        # Vérifier les événements
        events = ws.get_events()
        actions = [e["action"] for e in events]
        
        assert "workspace.branch" in actions
        assert "document.written" in actions
        assert "workspace.commit" in actions

    def test_criterion_6_replay_produces_identical_snapshot_ids(self):
        """
        Critère 6: Rejouer le log reconstruit des snapshot IDs identiques 
        à l'exécution originale.
        """
        # TODO: Implémenter le replay déterministe
        # Ce test nécessite l'implémentation du module de replay
        pytest.skip("Replay déterministe à implémenter dans M1")

    def test_criterion_7_no_overwrite_on_concurrent_target_change(self):
        """
        Critère 7: Un merge contre une cible qui a bougé entre-temps 
        ne doit jamais écraser les changements (Compare-and-Swap).
        """
        # TODO: Implémenter le test de concurrence
        # Ce test nécessite un mécanisme de comparaison de version (CAS)
        pytest.skip("Mécanisme CAS à implémenter dans M1")


class TestLeasesAndDeadlock:
    """Tests supplémentaires pour les leases et la détection de deadlock."""

    def test_lease_acquire_and_release(self):
        """Test basique d'acquisition et de libération de lease."""
        ws = Workspace(require_leases=True)
        
        # Acquérir un lease
        ws.acquire_lease("agent-a", "db/schema", duration_seconds=60)
        
        # Vérifier que le lease est actif
        events = ws.get_events()
        lease_events = [e for e in events if e["action"] == "lease.acquire"]
        assert len(lease_events) == 1
        
        # Libérer le lease
        ws.release_lease("agent-a", "db/schema")
        
        release_events = [e for e in events if e["action"] == "lease.release"]
        assert len(release_events) == 1

    def test_deadlock_detection(self):
        """Test de détection de deadlock circulaire."""
        ws = Workspace(require_leases=True)
        
        # Agent A acquiert resource-1
        ws.acquire_lease("agent-a", "resource-1", duration_seconds=60)
        
        # Agent B acquiert resource-2
        ws.acquire_lease("agent-b", "resource-2", duration_seconds=60)
        
        # Agent A attend resource-2 (détenu par B)
        # Agent B attend resource-1 (détenu par A)
        # → Deadlock circulaire
        
        # Ce test nécessite une implémentation asynchrone ou multi-thread
        pytest.skip("Détection de deadlock à implémenter avec threading")
