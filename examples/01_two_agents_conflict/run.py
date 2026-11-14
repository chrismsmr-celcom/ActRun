"""
ActRun - Exemple 01 : Deux agents, un conflit
=============================================

Scénario : Agent Marketing et Agent Logistique collaborent pour un événement.
"""
import sys
import os

# Ajouter le chemin pour importer actrun depuis le package local
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../python/src'))

from actrun.workspace import Workspace
from actrun.merge import ConflictError
from actrun.lease import LeaseError


def print_header(title: str):
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print('=' * 70)


def main():
    # === INITIALISATION ===
    ws = Workspace()
    
    # État initial : un événement à organiser
    ws.head.data.update({
        "event_name": "Tech Conference 2026",
        "lieu": "non défini",
        "budget": 10000,
        "invites_marketing": [],
        "invites_logistique": []
    })
    
    print_header("📍 ÉTAT INITIAL DU WORKSPACE")
    for key, value in ws.head.data.items():
        print(f"  {key}: {value}")

    # === ACTE 1 : Travail en parallèle (pas de conflit) ===
    print_header("ACTE 1 : Les agents travaillent en parallèle")
    
    # Agent Marketing crée une branche
    branch_marketing = ws.create_branch("agent_marketing", "setup-marketing")
    print(f"\n🔀 Agent Marketing crée une branche '{branch_marketing.name}'")
    
    # Agent Logistique crée une branche
    branch_logistique = ws.create_branch("agent_logistique", "setup-logistique")
    print(f"🔀 Agent Logistique crée une branche '{branch_logistique.name}'")
    
    # Marketing travaille sur le budget et ses invités (acquire lease pour être propre)
    print("\n💼 Agent Marketing réserve le budget et ses invités...")
    ws.acquire_lease("agent_marketing", "budget", duration_seconds=5.0)
    ws.acquire_lease("agent_marketing", "invites_marketing", duration_seconds=5.0)
    branch_marketing.set("budget", 15000)
    branch_marketing.set("invites_marketing", ["Alice", "Bob", "Charlie"])
    
    # Logistique travaille sur le lieu et ses invités
    print("🚚 Agent Logistique réserve le lieu et ses invités...")
    ws.acquire_lease("agent_logistique", "lieu", duration_seconds=5.0)
    ws.acquire_lease("agent_logistique", "invites_logistique", duration_seconds=5.0)
    branch_logistique.set("lieu", "Palais des Congrès")
    branch_logistique.set("invites_logistique", ["Dave", "Eve"])
    
    # Marketing committe en premier
    print("\n✅ Agent Marketing committe son travail...")
    ws.commit("agent_marketing", branch_marketing)
    ws.release_lease("agent_marketing", "budget")
    ws.release_lease("agent_marketing", "invites_marketing")
    
    # Logistique committe → AUTO-MERGE (pas de conflit car clés différentes)
    print("✅ Agent Logistique committe son travail (auto-merge)...")
    ws.commit("agent_logistique", branch_logistique)
    ws.release_lease("agent_logistique", "lieu")
    ws.release_lease("agent_logistique", "invites_logistique")
    
    print("\n📍 État après auto-merge réussi :")
    for key, value in ws.head.data.items():
        print(f"  {key}: {value}")

    # === ACTE 2 : Le conflit ===
    print_header("ACTE 2 : Les deux agents veulent modifier le lieu")
    
    # Les deux créent de nouvelles branches
    branch_m2 = ws.create_branch("agent_marketing", "change-venue-m")
    branch_l2 = ws.create_branch("agent_logistique", "change-venue-l")
    
    print("\n💼 Agent Marketing veut changer le lieu pour 'Centre International'...")
    branch_m2.set("lieu", "Centre International")
    
    print("🚚 Agent Logistique veut changer le lieu pour 'Parc des Expositions'...")
    branch_l2.set("lieu", "Parc des Expositions")
    
    # Marketing committe
    print("\n✅ Agent Marketing committe (succès)...")
    ws.commit("agent_marketing", branch_m2)
    
    # Logistique essaie de committer
    print("\n🔄 Agent Logistique tente de committer...")
    try:
        ws.commit("agent_logistique", branch_l2)
        print("❌ ERREUR : Le conflit aurait dû être détecté !")
    except ConflictError as e:
        print("🛡️ CONFLIT DÉTECTÉ ET BLOQUÉ !")
        print(f"   Message : {e}")
        print(f"   Clés en conflit : {e.conflicting_keys}")

    # === ACTE 3 : Résolution avec les leases ===
    print_header("ACTE 3 : Prévenir les conflits avec les leases")
    
    print("\n💡 La prochaine fois, les agents peuvent utiliser des leases :")
    print("   1. Agent Marketing acquiert un lease sur 'lieu'")
    print("   2. Agent Logistique essaie d'acquérir un lease sur 'lieu' → BLOQUÉ")
    print("   3. Logistique sait qu'il doit attendre ou négocier")
    
    # Démonstration
    print("\n🔒 Agent Marketing acquiert un lease sur 'lieu'...")
    ws.acquire_lease("agent_marketing", "lieu", duration_seconds=10.0)
    
    print("🔄 Agent Logistique tente d'acquérir un lease sur 'lieu'...")
    try:
        ws.acquire_lease("agent_logistique", "lieu", duration_seconds=10.0)
    except LeaseError as e:
        print("🛡️ BLOQUÉ : Logistique ne peut pas toucher à 'lieu'")
        print(f"   Message : {e}")
    
    ws.release_lease("agent_marketing", "lieu")
    print("\n🔓 Marketing libère le lease, Logistique peut maintenant l'acquérir")

    # === RÉCAPITULATIF ===
    print_header("📜 RÉCAPITULATIF : Journal complet des événements")
    events = ws.get_events()
    print(f"\n{len(events)} événements enregistrés :\n")
    
    for i, e in enumerate(events, 1):
        print(f"{i:2d}. [{e.action}] par {e.agent_id}")
        print(f"    {e.payload}")

    print_header("🎉 FIN DE LA DÉMONSTRATION")
    print("\nActRun a permis à deux agents de :")
    print("  ✅ Travailler en parallèle sans se gêner (auto-merge)")
    print("  ✅ Éviter les écrasements silencieux (détection de conflits)")
    print("  ✅ Réserver des ressources (leases avec expiration)")
    print("  ✅ Avoir une traçabilité complète (journal immuable)")
    print("\n" + "=" * 70 + "\n")

def export_trace():
    """Exporte le journal au format JSONL pour analyse par actrun-trace"""
    output_path = os.path.join(os.path.dirname(__file__), "trace.jsonl")
    with open(output_path, "w", encoding="utf-8") as f:
        for event in ws.get_events():
            f.write(event.to_jsonl() + "\n")
    print(f"\n💾 Trace exportée dans : {output_path}")
    print(f"   Analyse avec : cargo run --release -- {output_path}")
    
    export_trace()
    
if __name__ == "__main__":
    main()
