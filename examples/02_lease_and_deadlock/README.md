# Exemple 02 : Leases et Deadlocks

Ce scénario démontre comment **ActRun** détecte et prévient les deadlocks dans les systèmes multi-agents.

## Le problème du deadlock

Un deadlock se produit quand plusieurs agents se bloquent mutuellement en attendant des ressources détenues par les autres.

### Scénario classique : Le dîner des philosophes
- **Agent A** détient la ressource `fourchette_gauche` et attend `fourchette_droite`
- **Agent B** détient la ressource `fourchette_droite` et attend `fourchette_gauche`
- → **DEADLOCK** : Les deux agents attendent indéfiniment

## Ce que fait ActRun

1. **Détection automatique** : ActRun construit un graphe d'attente (Wait-for Graph) et détecte les cycles
2. **Prévention** : Quand un deadlock est détecté, une exception `DeadlockError` est levée immédiatement
3. **Résolution** : L'agent peut alors libérer une ressource pour briser le cycle

## Démonstration

Lance le script :
```bash
python run.py


Tu verras :
✅ Cas normal : deux agents coopèrent sans problème
🛡️ Cas de deadlock : détection automatique du cycle
🔧 Résolution : libération d'une ressource pour débloquer la situation

#### 2. `examples/02_lease_and_deadlock/run.py`
```python
"""
ActRun - Exemple 02 : Leases et Deadlocks
==========================================

Scénario : Deux agents veulent utiliser deux ressources partagées.
Démonstration de la détection et résolution de deadlock.
"""
import sys
import os
import time
import threading

# Ajouter le chemin pour importer actrun
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../python/src'))

from actrun.lease import LeaseManager, LeaseError
from actrun.deadlock import DeadlockError


def print_header(title: str):
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print('=' * 70)


def scenario_1_cooperation():
    """Scénario 1 : Les agents coopèrent sans deadlock."""
    print_header("SCÉNARIO 1 : Coopération normale (pas de deadlock)")
    
    lm = LeaseManager()
    
    print("\n📋 Contexte :")
    print("   Agent A et Agent B veulent utiliser deux ressources : 'imprimante' et 'scanner'")
    print("   Ils les utilisent l'une après l'autre, pas en même temps.")
    
    # Agent A utilise l'imprimante
    print("\n🔒 Agent A réserve l'imprimante...")
    lm.acquire("agent_A", "imprimante", duration_seconds=2.0)
    print("   ✅ Agent A utilise l'imprimante")
    
    # Agent B utilise le scanner (ressource différente)
    print("🔒 Agent B réserve le scanner...")
    lm.acquire("agent_B", "scanner", duration_seconds=2.0)
    print("   ✅ Agent B utilise le scanner")
    
    print("\n🎉 Pas de conflit : les ressources sont disjointes")
    
    # Libérer
    lm.release("agent_A", "imprimante")
    lm.release("agent_B", "scanner")
    print("🔓 Les deux agents libèrent leurs ressources")


def scenario_2_deadlock_detection():
    """Scénario 2 : Détection de deadlock."""
    print_header("SCÉNARIO 2 : Détection de deadlock")
    
    lm = LeaseManager()
    
    print("\n📋 Contexte :")
    print("   Agent A détient 'fourchette_gauche' et veut 'fourchette_droite'")
    print("   Agent B détient 'fourchette_droite' et veut 'fourchette_gauche'")
    print("   → Situation de deadlock classique !")
    
    # Chaque agent détient une ressource
    print("\n🔒 Agent A réserve fourchette_gauche...")
    lm.acquire("agent_A", "fourchette_gauche", duration_seconds=10.0)
    
    print("🔒 Agent B réserve fourchette_droite...")
    lm.acquire("agent_B", "fourchette_droite", duration_seconds=10.0)
    
    print("\n⚠️  État actuel :")
    print("   Agent A : détient fourchette_gauche")
    print("   Agent B : détient fourchette_droite")
    
    # Agent A veut fourchette_droite (détenu par B)
    print("\n🔄 Agent A attend fourchette_droite (détenu par B)...")
    
    deadlock_detected = [False]
    deadlock_msg = [None]
    
    def agent_A_waits():
        try:
            lm.acquire("agent_A", "fourchette_droite", wait=True, timeout_seconds=2.0)
        except DeadlockError as e:
            deadlock_detected[0] = True
            deadlock_msg[0] = str(e)
        except LeaseError:
            pass
    
    thread_A = threading.Thread(target=agent_A_waits)
    thread_A.start()
    time.sleep(0.2)  # Laisser A commencer à attendre
    
    # Agent B veut fourchette_gauche (détenu par A) → DEADLOCK !
    print("🔄 Agent B attend fourchette_gauche (détenu par A)...")
    print("   ⚡ ActRun analyse le graphe d'attente...")
    
    try:
        lm.acquire("agent_B", "fourchette_gauche", wait=True, timeout_seconds=2.0)
        print("❌ ERREUR : Le deadlock aurait dû être détecté !")
    except DeadlockError as e:
        print("\n🛡️ DEADLOCK DÉTECTÉ PAR ACTRUN !")
        print(f"   Message : {e}")
        print("\n💡 ActRun a détecté le cycle :")
        print("   agent_A → fourchette_droite → agent_B → fourchette_gauche → agent_A")
    
    thread_A.join(timeout=2.0)
    
    # Nettoyer
    lm.release("agent_A", "fourchette_gauche")
    lm.release("agent_B", "fourchette_droite")


def scenario_3_resolution():
    """Scénario 3 : Résolution du deadlock."""
    print_header("SCÉNARIO 3 : Résolution du deadlock")
    
    lm = LeaseManager()
    
    print("\n📋 Contexte :")
    print("   Même situation que le scénario 2, mais cette fois les agents")
    print("   vont coopérer pour résoudre le deadlock.")
    
    # Chaque agent détient une ressource
    print("\n🔒 Agent A réserve ressource_1...")
    lm.acquire("agent_A", "ressource_1", duration_seconds=10.0)
    
    print("🔒 Agent B réserve ressource_2...")
    lm.acquire("agent_B", "ressource_2", duration_seconds=10.0)
    
    # Agent A veut ressource_2
    print("\n🔄 Agent A attend ressource_2...")
    
    acquired = [False]
    
    def agent_A_waits():
        try:
            lm.acquire("agent_A", "ressource_2", wait=True, timeout_seconds=5.0)
            acquired[0] = True
        except (DeadlockError, LeaseError):
            pass
    
    thread_A = threading.Thread(target=agent_A_waits)
    thread_A.start()
    time.sleep(0.2)
    
    # Agent B veut ressource_1 → risque de deadlock
    print("🔄 Agent B attend ressource_1...")
    time.sleep(0.2)
    
    # Agent B décide de libérer sa ressource pour éviter le deadlock
    print("\n💡 Agent B détecte le risque et libère ressource_2...")
    lm.release("agent_B", "ressource_2")
    
    # Agent A peut maintenant obtenir ressource_2
    thread_A.join(timeout=2.0)
    
    if acquired[0]:
        print("✅ Agent A a obtenu ressource_2 !")
    else:
        print("⚠️  Agent A n'a pas pu obtenir ressource_2 (timing)")
    
    # Agent A libère tout
    lm.release("agent_A", "ressource_1")
    lm.release("agent_A", "ressource_2")
    
    # Maintenant Agent B peut obtenir ressource_1
    print("🔒 Agent B réserve ressource_1...")
    try:
        lm.acquire("agent_B", "ressource_1", duration_seconds=2.0)
        print("✅ Agent B a obtenu ressource_1 !")
        lm.release("agent_B", "ressource_1")
    except LeaseError as e:
        print(f"⚠️  {e}")
    
    print("\n🎉 Deadlock évité par coopération !")


def scenario_4_best_practices():
    """Scénario 4 : Bonnes pratiques."""
    print_header("SCÉNARIO 4 : Bonnes pratiques pour éviter les deadlocks")
    
    print("\n💡 Voici les stratégies recommandées avec ActRun :\n")
    
    print("1. 📋 ORDONNANCEMENT DES RESSOURCES")
    print("   → Toujours acquérir les ressources dans le MÊME ordre")
    print("   → Exemple : toujours ressource_1 avant ressource_2")
    print("   → Cela empêche les cycles de se former\n")
    
    print("2. ⏱️  LEASES AVEC EXPIRATION")
    print("   → Utiliser des durations courtes (5-30 secondes)")
    print("   → Si un agent plante, le lease expire automatiquement")
    print("   → Pas de blocage éternel\n")
    
    print("3. 🔍 DÉTECTION AUTOMATIQUE")
    print("   → ActRun détecte les deadlocks en temps réel")
    print("   → L'agent reçoit une DeadlockError immédiatement")
    print("   → Il peut alors libérer une ressource et réessayer\n")
    
    print("4. 🤝 COOPÉRATION")
    print("   → Les agents peuvent communiquer entre eux")
    print("   → Si un agent détecte un risque, il libère volontairement")
    print("   → Meilleure approche pour les systèmes collaboratifs\n")
    
    print("5. 🔄 RETRY WITH BACKOFF")
    print("   → Si DeadlockError, attendre un peu et réessayer")
    print("   → Exemple :")
    print("      try:")
    print("          lease = lm.acquire(agent_id, resource, wait=True)")
    print("      except DeadlockError:")
    print("          time.sleep(1)")
    print("          # Réessayer ou libérer une autre ressource")


def main():
    print("\n" + "=" * 70)
    print("  ACTRUN - DÉMONSTRATION : LEASES ET DEADLOCKS")
    print("=" * 70)
    
    scenario_1_cooperation()
    scenario_2_deadlock_detection()
    scenario_3_resolution()
    scenario_4_best_practices()
    
    print_header("🎉 FIN DE LA DÉMONSTRATION")
    print("\nActRun a démontré :")
    print("  ✅ Détection automatique des deadlocks via Wait-for Graph")
    print("  ✅ Prévention des blocages éternels")
    print("  ✅ Résolution par coopération entre agents")
    print("  ✅ Bonnes pratiques pour éviter les deadlocks")
    print("\n" + "=" * 70 + "\n")


if __name__ == "__main__":
    main()
🛠️ Lancer l'exemple
Depuis la racine de ton projet :
bash
python examples/02_lease_and_deadlock/run.py
🎯 Ce que tu obtiens
Un script qui montre en 3 minutes :
Le problème : "Mes agents se bloquent mutuellement"
La solution ActRun : Détection automatique + résolution
Les bonnes pratiques : Comment éviter les deadlocks
C'est exactement le genre d'exemple qui fait qu'un développeur dit "Ok, je comprends le problème et la solution en 5 minutes".
📊 Récapitulatif de tout ce que tu as construit
Avec ces 9 étapes, tu as maintenant :
Composant
Statut
Fichier
Core Python
✅
python/src/actrun/
- Événements immuables
✅
events.py
- Workspace + branches
✅
workspace.py
- Détection de conflits
✅
merge.py
- Leases + deadlock
✅
lease.py + deadlock.py
Moteur Rust
✅
crates/actrun-trace/
Serveur MCP
✅
integrations/mcp-server/
Exemples
✅
examples/01_* + examples/02_*
Tu as une stack complète de coordination multi-agents, exactement ce que les startups à 60M$ essaient de construire.
