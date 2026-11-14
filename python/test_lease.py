# python/test_lease.py
import time
from src.actrun.workspace import Workspace
from src.actrun.lease import LeaseError

print("=" * 60)
print("TEST 1 : Protection par Lease")
print("=" * 60)

ws = Workspace()
ws.head.data.update({"shared_resource": "initial_value"})

# Alpha crée une branche
branch_alpha = ws.create_branch("agent_alpha", "task-alpha")

# Alpha essaie de modifier sans lease → DOIT ÉCHOUER
print("\n🔄 Alpha tente de modifier sans lease...")
try:
    branch_alpha.set("shared_resource", "modified_by_alpha")
    print("❌ ERREUR : Alpha aurait dû être bloqué !")
except LeaseError as e:
    print(f"✅ SUCCÈS : Alpha bloqué correctement")
    print(f"   Message : {e}")

# Alpha acquiert un lease
print("\n🔒 Alpha acquiert un lease sur 'shared_resource'...")
ws.acquire_lease("agent_alpha", "shared_resource", duration_seconds=5.0)
print("✅ Lease acquis")

# Maintenant Alpha peut modifier
print("\n🔄 Alpha modifie la ressource (avec lease)...")
branch_alpha.set("shared_resource", "modified_by_alpha")
print(f"✅ Modification réussie : {branch_alpha.current_data}")

# Beta essaie d'acquérir un lease sur la MÊME ressource → DOIT ÉCHOUER
print("\n🔄 Beta tente d'acquérir un lease sur la même ressource...")
try:
    ws.acquire_lease("agent_beta", "shared_resource", duration_seconds=5.0)
    print("❌ ERREUR : Beta aurait dû être bloqué !")
except LeaseError as e:
    print(f"✅ SUCCÈS : Beta bloqué (ressource déjà verrouillée)")
    print(f"   Message : {e}")

print("\n" + "=" * 60)
print("TEST 2 : Expiration Automatique du Lease")
print("=" * 60)

# Alpha libère son lease
ws.release_lease("agent_alpha", "shared_resource")
print("\n🔓 Alpha libère son lease")

# Alpha acquiert un lease très court (1 seconde)
print("\n🔒 Alpha acquiert un lease de 1 seconde...")
ws.acquire_lease("agent_alpha", "shared_resource", duration_seconds=1.0)

# Beta essaie tout de suite → BLOQUÉ
print("\n🔄 Beta tente d'acquérir immédiatement...")
try:
    ws.acquire_lease("agent_beta", "shared_resource", duration_seconds=5.0)
    print("❌ ERREUR : Beta aurait dû être bloqué !")
except LeaseError:
    print("✅ Beta bloqué (lease encore actif)")

# On attend que le lease expire
print("\n⏳ Attente de 1.5 secondes pour expiration du lease...")
time.sleep(1.5)

# Beta réessaie → DOIT RÉUSSIR
print("\n🔄 Beta tente d'acquérir après expiration...")
try:
    ws.acquire_lease("agent_beta", "shared_resource", duration_seconds=5.0)
    print("✅ SUCCÈS : Beta a acquis le lease (l'ancien a expiré)")
except LeaseError as e:
    print(f"❌ ERREUR : Beta aurait dû réussir ! {e}")

print("\n" + "=" * 60)
print("TEST 3 : Journal Complet des Événements")
print("=" * 60)

print("\n📜 Tous les événements (workspace + leases) :")
for e in ws.get_events():
    print(f"  [{e.timestamp[:19]}] {e.action} par {e.agent_id}")
    print(f"     → {e.payload}")

print("\n" + "=" * 60)
print("🎉 TOUS LES TESTS PASSENT !")
print("=" * 60)
