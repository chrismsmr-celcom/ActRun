"""Test de la persistance SQLite."""
import os
import tempfile
from pathlib import Path
from src.actrun.persistence import PersistentWorkspace


def test_basic_persistence():
    """Test basique : créer, fermer, rouvrir."""
    print("=" * 60)
    print("TEST 1 : Persistance basique")
    print("=" * 60)
    
    # Créer un fichier temporaire
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        # Session 1 : Créer des données
        print("\n📝 Session 1 : Création de données...")
        with PersistentWorkspace(db_path) as ws:
            ws.head.data.update({"status": "initialized"})
            
            branch = ws.create_branch("agent_A", "feature-1")
            branch.set("task_1", "done")
            branch.set("task_2", "in_progress")
            
            snapshot = ws.commit("agent_A", branch)
            print(f"   ✅ Commit créé : {snapshot.version_id[:8]}")
            print(f"   📊 HEAD : {ws.head.data}")
            
            ws.acquire_lease("agent_A", "resource_X", duration_seconds=10.0)
            print(f"   🔒 Lease acquis sur 'resource_X'")
        
        print(f"\n💾 Base de données sauvegardée dans : {db_path}")
        print(f"   Taille : {os.path.getsize(db_path)} bytes")
        
        # Session 2 : Rouvrir et vérifier
        print("\n🔄 Session 2 : Reprise des données...")
        with PersistentWorkspace(db_path) as ws:
            print(f"   📊 HEAD restauré : {ws.head.data}")
            print(f"   📜 Nombre de snapshots : {ws.get_snapshot_count()}")
            print(f"   📜 Nombre d'événements : {ws.get_event_count()}")
            print(f"   🔒 Nombre de leases actifs : {ws.get_active_lease_count()}")
            
            # Vérifier que les données sont bien là
            assert ws.head.data.get("task_1") == "done", "Données non restaurées !"
            assert ws.get_snapshot_count() >= 2, "Snapshots manquants !"
            assert ws.get_active_lease_count() == 1, "Lease non restauré !"
            
            print("\n✅ Toutes les données ont été restaurées avec succès !")
        
    finally:
        # Nettoyer
        if os.path.exists(db_path):
            os.remove(db_path)
        # SQLite crée aussi des fichiers -wal et -shm
        for ext in ['-wal', '-shm']:
            wal_path = db_path + ext
            if os.path.exists(wal_path):
                os.remove(wal_path)


def test_crash_recovery():
    """Test de reprise après 'crash' (fermeture brutale)."""
    print("\n" + "=" * 60)
    print("TEST 2 : Reprise après crash simulé")
    print("=" * 60)
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        # Session 1 : Travailler
        print("\n📝 Session 1 : Travail normal...")
        ws = PersistentWorkspace(db_path)
        
        branch = ws.create_branch("agent_B", "critical-task")
        branch.set("important_data", "do_not_lose_this")
        ws.commit("agent_B", branch)
        print("   ✅ Données critiques commitées")
        
        # Simuler un crash (pas de close())
        print("\n💥 Simulation de crash (fermeture sans close)...")
        del ws  # Force la libération sans appel à close()
        
        # Session 2 : Reprise
        print("\n🔄 Session 2 : Reprise après crash...")
        ws2 = PersistentWorkspace(db_path)
        
        print(f"   📊 HEAD restauré : {ws2.head.data}")
        assert ws2.head.data.get("important_data") == "do_not_lose_this"
        print("   ✅ Données critiques récupérées !")
        
        ws2.close()
        
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)
        for ext in ['-wal', '-shm']:
            wal_path = db_path + ext
            if os.path.exists(wal_path):
                os.remove(wal_path)


def test_jsonl_export():
    """Test de l'export JSONL pour le moteur Rust."""
    print("\n" + "=" * 60)
    print("TEST 3 : Export JSONL pour le moteur Rust")
    print("=" * 60)
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    jsonl_path = db_path.replace('.db', '.jsonl')
    
    try:
        # Créer des données
        print("\n📝 Création de données...")
        with PersistentWorkspace(db_path) as ws:
            ws.create_branch("agent_X", "branch-1")
            ws.acquire_lease("agent_X", "res_1")
            ws.release_lease("agent_X", "res_1")
        
        # Exporter en JSONL
        print("\n💾 Export vers JSONL...")
        with PersistentWorkspace(db_path) as ws:
            count = ws.export_events_jsonl(jsonl_path)
            print(f"   ✅ {count} événements exportés")
        
        # Vérifier le contenu
        print(f"\n📄 Contenu de {Path(jsonl_path).name} :")
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for i, line in enumerate(lines[:5], 1):
                print(f"   {i}. {line.strip()[:80]}...")
        
        print(f"\n💡 Ce fichier peut être analysé par le moteur Rust :")
        print(f"   cargo run --release -- {jsonl_path}")
        
    finally:
        for path in [db_path, jsonl_path]:
            if os.path.exists(path):
                os.remove(path)
        for ext in ['-wal', '-shm']:
            wal_path = db_path + ext
            if os.path.exists(wal_path):
                os.remove(wal_path)


if __name__ == "__main__":
    test_basic_persistence()
    test_crash_recovery()
    test_jsonl_export()
    
    print("\n" + "=" * 60)
    print("🎉 TOUS LES TESTS DE PERSISTANCE PASSENT !")
    print("=" * 60)
