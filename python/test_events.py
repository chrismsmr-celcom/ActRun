# python/test_events.py
from src.actrun.events import ActRunEvent

# Créer un événement
event = ActRunEvent(
    agent_id="agent_alpha",
    action="workspace.branch",
    payload={"branch_name": "feature-x", "base_version": 1},
    metadata={"session_id": "sess_123"}
)

print("✅ Événement créé avec succès !")
print("ID :", event.event_id)
print("Format JSONL :", event.to_jsonl())
