import json
import hashlib
from typing import Dict, List
from .models import CerbereCohortEvent

class WorkspaceReplayer:
    def __init__(self):
        # État reconstruit : { branch_name: { path: content_hash } }
        self.branches: Dict[str, Dict[str, str]] = {"main": {}}
        self.content_store: Dict[str, str] = {} # hash -> content (pour vérification)

    def _compute_hash(self, content: str) -> str:
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def _compute_snapshot_id(self, branch: str, state: Dict[str, str]) -> str:
        # L'ID du snapshot doit être déterministe basé sur l'état du branch
        state_str = json.dumps(state, sort_keys=True)
        return hashlib.sha256(f"{branch}:{state_str}".encode('utf-8')).hexdigest()[:16]

    def replay_from_jsonl(self, filepath: str) -> Dict[str, str]:
        """Rejoue les événements et retourne les snapshot_ids finaux par branche."""
        with open(filepath, 'r', encoding='utf-8') as f:
            events = [json.loads(line) for line in f]
        
        # Trier par timestamp pour garantir l'ordre chronologique
        events.sort(key=lambda x: x["timestamp"])

        for evt in events:
            action = evt["action"]
            payload = evt["payload"]
            agent = evt["agent_id"]

            if action == "workspace.branch":
                branch_name = payload["branch_name"]
                source = payload.get("source", "main")
                self.branches[branch_name] = self.branches[source].copy()
            
            elif action == "document.written":
                branch = payload["branch"]
                path = payload["path"]
                content = payload["content"]
                
                if branch not in self.branches:
                    self.branches[branch] = {}
                
                content_hash = self._compute_hash(content)
                self.branches[branch][path] = content_hash
                self.content_store[content_hash] = content

            elif action == "workspace.commit":
                # Un commit fige l'état actuel, on pourrait enregistrer le snapshot_id ici
                branch = payload["branch"]
                snapshot_id = self._compute_snapshot_id(branch, self.branches[branch])
                print(f"[REPLAY] Commit sur '{branch}' par {agent} -> Snapshot ID: {snapshot_id}")

        # Calcul final des snapshot IDs
        final_snapshots = {
            branch: self._compute_snapshot_id(branch, state) 
            for branch, state in self.branches.items()
        }
        return final_snapshots

# Exemple d'utilisation :
# replayer = WorkspaceReplayer()
# snapshots = replayer.replay_from_jsonl("run.jsonl")
# print("Snapshots reconstruits :", snapshots)
