# python/test_workspace.py
from src.actrun.workspace import Workspace

# 1. Initialiser le workspace
ws = Workspace()
print(f"📍 État initial (HEAD) : {ws.head.data}")

# 2. Agent Alpha crée une branche et travaille dessus
branch_alpha = ws.create_branch(agent_id="agent_alpha", branch_name="feature-x")
branch_alpha.set("task_1", "done")
branch_alpha.set("task_2", "in_progress")
print(f"🔀 Branche Alpha : {branch_alpha.current_data}")
print(f"📍 HEAD (non modifié) : {ws.head.data}")

# 3. Agent Beta crée une branche en parallèle
branch_beta = ws.create_branch(agent_id="agent_beta", branch_name="feature-y")
branch_beta.set("task_3", "done")
print(f"🔀 Branche Beta : {branch_beta.current_data}")

# 4. Alpha committe son travail
snapshot_alpha = ws.commit(agent_id="agent_alpha", branch=branch_alpha)
print(f"\n✅ Alpha a commité. Nouvelle version HEAD : {ws.head.version_id}")
print(f"📍 Nouvel état HEAD : {ws.head.data}")

# 5. Beta voit-il les changements d'Alpha ?
# Non, car Beta a créé sa branche AVANT le commit d'Alpha.
print(f"🔀 Beta voit toujours : {branch_beta.current_data}")

# 6. Afficher le journal d'événements
print("\n📜 Journal des événements :")
for e in ws.get_events():
    print(f"  - {e.action} par {e.agent_id} : {e.payload}")
