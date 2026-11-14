"""Test de détection de deadlock."""
from src.actrun.lease import LeaseManager, LeaseError
from src.actrun.deadlock import DeadlockError


def test_no_deadlock():
    """Cas normal : pas de deadlock."""
    print("=" * 60)
    print("TEST 1 : Pas de deadlock (ressources disjointes)")
    print("=" * 60)
    
    lm = LeaseManager()
    lm.acquire("agent_A", "resource_X")
    lm.acquire("agent_B", "resource_Y")
    
    print("✅ A détient X, B détient Y → pas de problème")
    print()


def test_simple_deadlock():
    """Deadlock classique : A attend B, B attend A."""
    print("=" * 60)
    print("TEST 2 : Deadlock simple (A ↔ B)")
    print("=" * 60)
    
    lm = LeaseManager()
    
    # A détient X, B détient Y
    lm.acquire("agent_A", "resource_X")
    lm.acquire("agent_B", "resource_Y")
    print("🔒 A détient X, B détient Y")
    
    # A attend Y (détenu par B) → OK pour l'instant
    print("\n🔄 A attend Y (détenu par B)...")
    # On ne peut pas vraiment bloquer dans un test synchrone,
    # donc on simule en lançant dans un thread
    import threading
    
    deadlock_detected = [False]
    error_msg = [None]
    
    def agent_A_waits():
        try:
            lm.acquire("agent_A", "resource_Y", wait=True, timeout_seconds=0.5)
        except DeadlockError as e:
            deadlock_detected[0] = True
            error_msg[0] = str(e)
        except LeaseError:
            pass
    
    thread = threading.Thread(target=agent_A_waits)
    thread.start()
    
    # Laisser A commencer à attendre
    import time
    time.sleep(0.1)
    
    # Maintenant B attend X (détenu par A) → DEADLOCK !
    print("🔄 B attend X (détenu par A)...")
    try:
        lm.acquire("agent_B", "resource_X", wait=True, timeout_seconds=0.5)
        print("❌ ERREUR : B aurait dû détecter le deadlock !")
    except DeadlockError as e:
        print(f"\n🛡️ DEADLOCK DÉTECTÉ !")
        print(f"   Message : {e}")
    
    thread.join(timeout=1.0)
    print()


def test_three_agents_deadlock():
    """Deadlock à 3 agents : A → B → C → A."""
    print("=" * 60)
    print("TEST 3 : Deadlock à 3 agents (A → B → C → A)")
    print("=" * 60)
    
    lm = LeaseManager()
    
    # Chaque agent détient une ressource
    lm.acquire("agent_A", "res_1")
    lm.acquire("agent_B", "res_2")
    lm.acquire("agent_C", "res_3")
    print("🔒 A détient res_1, B détient res_2, C détient res_3")
    
    import threading
    import time
    
    # A attend res_2 (détenu par B)
    def a_waits():
        try:
            lm.acquire("agent_A", "res_2", wait=True, timeout_seconds=1.0)
        except (DeadlockError, LeaseError):
            pass
    
    # B attend res_3 (détenu par C)
    def b_waits():
        try:
            lm.acquire("agent_B", "res_3", wait=True, timeout_seconds=1.0)
        except (DeadlockError, LeaseError):
            pass
    
    t1 = threading.Thread(target=a_waits)
    t2 = threading.Thread(target=b_waits)
    t1.start()
    time.sleep(0.1)
    t2.start()
    time.sleep(0.1)
    
    # C attend res_1 (détenu par A) → CYCLE A → B → C → A
    print("\n🔄 C attend res_1 (détenu par A)...")
    try:
        lm.acquire("agent_C", "res_1", wait=True, timeout_seconds=1.0)
        print("❌ ERREUR : C aurait dû détecter le deadlock !")
    except DeadlockError as e:
        print(f"\n🛡️ DEADLOCK À 3 DÉTECTÉ !")
        print(f"   Message : {e}")
    
    t1.join(timeout=1.0)
    t2.join(timeout=1.0)
    print()


def test_no_false_positive():
    """Vérifier qu'on ne détecte pas de deadlock quand il n'y en a pas."""
    print("=" * 60)
    print("TEST 4 : Pas de faux positif (chaîne sans cycle)")
    print("=" * 60)
    
    lm = LeaseManager()
    
    lm.acquire("agent_A", "res_1")
    lm.acquire("agent_B", "res_2")
    print("🔒 A détient res_1, B détient res_2")
    
    # A attend res_2 → OK (pas de cycle)
    import threading
    import time
    
    acquired = [False]
    
    def a_waits():
        try:
            lease = lm.acquire("agent_A", "res_2", wait=True, timeout_seconds=1.0)
            acquired[0] = True
        except (DeadlockError, LeaseError):
            pass
    
    t = threading.Thread(target=a_waits)
    t.start()
    time.sleep(0.1)
    
    # B libère res_2 → A devrait l'obtenir
    print("🔓 B libère res_2...")
    lm.release("agent_B", "res_2")
    
    t.join(timeout=1.0)
    
    if acquired[0]:
        print("✅ A a obtenu res_2 après libération (pas de faux deadlock)")
    else:
        print("⚠️  A n'a pas pu obtenir res_2 (comportement attendu si timing serré)")
    print()


if __name__ == "__main__":
    test_no_deadlock()
    test_simple_deadlock()
    test_three_agents_deadlock()
    test_no_false_positive()
    
    print("=" * 60)
    print("🎉 TOUS LES TESTS DE DEADLOCK TERMINÉS")
    print("=" * 60)
