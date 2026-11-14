# python/test_merge.py
from src.actrun.workspace import Workspace
from src.actrun.merge import ConflictError

# 1. Initialiser avec des données de base
ws = Workspace()
# On simule un état initial pré-rempli pour l'exemple
ws.head.data.update({"shared_resource": "v1", "alpha_task": "todo", "beta_task": "todo"})
base_version_id = ws.head.version_id
print(f"📍 État initial HEAD : {ws.head.data}\n")

# 2. Alpha et Beta créent des branches en même temps (même base_version)
branch_alpha = ws.create_branch("agent_alpha", "fix-alpha")
branch_beta = ws.create_branch("agent_beta", "fix-beta")

# 3. Alpha modifie sa tâche ET la ressource partagée
branch_alpha.set("alpha_task", "done")
branch_alpha.set("shared_resource", "modified_by_alpha")

# 4. Beta modifie SA tâche ET la MÊME ressource partagée (CONFLIT !)
branch_beta.set("beta_task", "done")
branch_beta.set("shared_resource", "modified_by_beta")

# 5. Alpha commite en premier (Succès)
try:
    ws.commit("agent_alpha", branch_alpha)
    print("✅ Alpha a commité avec succès.")
    print(f"   HEAD est maintenant : {ws.head.data}\n")
except ConflictError as e:
    print(f"❌ Erreur inattendue pour Alpha : {e}")

# 6. Beta essaie de commiter (Doit ÉCHOUER à cause du conflit sur "shared_resource")
print("🔄 Beta tente de commiter...")
try:
    ws.commit("agent_beta", branch_beta)
    print("❌ ERREUR : Beta aurait dû être bloqué !")
except ConflictError as e:
    print(f"🛡️ SUCCÈS : Conflit correctement détecté et bloqué !")
    print(f"   Message : {e}")
    print(f"   Clés en conflit : {e.conflicting_keys}\n")

# 7. Démonstration d'Auto-Merge (Beta corrige sa branche pour éviter le conflit)
print("🔄 Beta corrige sa branche (ne touche plus à shared_resource) et réessaie...")
branch_beta_safe = ws.create_branch("agent_beta", "fix-beta-safe")
branch_beta_safe.set("beta_task", "done_final") # Modifie uniquement sa propre clé

try:
    ws.commit("agent_beta", branch_beta_safe)
    print("✅ Beta a commité avec succès (Auto-Merge).")
    print(f"   État final HEAD fusionné : {ws.head.data}")
except ConflictError as e:
    print(f"❌ Erreur inattendue : {e}")

print("\n📜 Journal final des événements :")
for e in ws.get_events():
    print(f"  - [{e.action}] {e.agent_id} -> {e.payload}")
