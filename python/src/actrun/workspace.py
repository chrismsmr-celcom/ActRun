# python/src/actrun/workspace.py
import copy
import uuid
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from .events import ActRunEvent

@dataclass(frozen=True)
class Snapshot:
    """Une version immuable de l'état partagé."""
    version_id: str
    data: Dict[str, Any]
    parent_version: Optional[str] = None

class Branch:
    """Une copie de travail isolée pour un agent."""
    def __init__(self, name: str, base_snapshot: Snapshot):
        self.name = name
        self.current_data = copy.deepcopy(base_snapshot.data)
        self.base_version = base_snapshot.version_id

    def set(self, key: str, value: Any) -> None:
        self.current_data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self.current_data.get(key, default)

    def delete(self, key: str) -> None:
        self.current_data.pop(key, None)

class Workspace:
    """
    Le gestionnaire central du workspace partagé.
    Maintient l'historique des snapshots et permet la création de branches.
    """
    def __init__(self):
        # Historique immuable de tous les snapshots
        self._snapshots: Dict[str, Snapshot] = {}
        
        # Snapshot initial (état vide)
        initial_snapshot = Snapshot(
            version_id=str(uuid.uuid4()),
            data={},
            parent_version=None
        )
        self._snapshots[initial_snapshot.version_id] = initial_snapshot
        self._head_version = initial_snapshot.version_id
        
        # Journal des événements (optionnel, pour traçabilité)
        self._events: List[ActRunEvent] = []

    @property
    def head(self) -> Snapshot:
        return self._snapshots[self._head_version]

    def create_branch(self, agent_id: str, branch_name: str) -> Branch:
        """Crée une nouvelle branche à partir de l'état actuel (HEAD)."""
        branch = Branch(name=branch_name, base_snapshot=self.head)
        
        # Enregistrer l'événement
        event = ActRunEvent(
            agent_id=agent_id,
            action="workspace.branch",
            payload={
                "branch_name": branch_name,
                "base_version": self._head_version
            }
        )
        self._events.append(event)
        return branch

    def commit(self, agent_id: str, branch: Branch) -> Snapshot:
        """
        Valide les modifications d'une branche comme un nouveau snapshot officiel.
        Met à jour HEAD.
        """
        new_snapshot = Snapshot(
            version_id=str(uuid.uuid4()),
            data=copy.deepcopy(branch.current_data),
            parent_version=self._head_version
        )
        self._snapshots[new_snapshot.version_id] = new_snapshot
        self._head_version = new_snapshot.version_id
        
        event = ActRunEvent(
            agent_id=agent_id,
            action="workspace.commit",
            payload={
                "version_id": new_snapshot.version_id,
                "parent_version": new_snapshot.parent_version,
                "keys_modified": list(branch.current_data.keys())
            }
        )
        self._events.append(event)
        return new_snapshot

    def get_events(self) -> List[ActRunEvent]:
        return self._events.copy()
