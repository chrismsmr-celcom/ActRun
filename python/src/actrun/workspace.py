# python/src/actrun/workspace.py
import copy
import uuid
from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from .events import ActRunEvent
from .merge import detect_and_merge, MergeResult, ConflictError
from .lease import LeaseManager, LeaseError

@dataclass(frozen=True)
class Snapshot:
    """Une version immuable de l'état partagé."""
    version_id: str
    data: Dict[str, Any]
    parent_version: Optional[str] = None

class Branch:
    """Une copie de travail isolée pour un agent."""
    def __init__(self, name: str, base_snapshot: Snapshot, lease_manager: LeaseManager, agent_id: str):
        self.name = name
        self.current_data = copy.deepcopy(base_snapshot.data)
        self.base_version = base_snapshot.version_id
        self._lease_manager = lease_manager
        self._agent_id = agent_id

    def set(self, key: str, value: Any) -> None:
        """
        Modifie une clé. Nécessite un lease actif sur cette clé.
        """
        if not self._lease_manager.check_lease(self._agent_id, key):
            raise LeaseError(
                f"L'agent '{self._agent_id}' doit acquérir un lease sur '{key}' "
                f"avant de pouvoir le modifier."
            )
        self.current_data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self.current_data.get(key, default)

    def delete(self, key: str) -> None:
        if not self._lease_manager.check_lease(self._agent_id, key):
            raise LeaseError(
                f"L'agent '{self._agent_id}' doit acquérir un lease sur '{key}' "
                f"avant de pouvoir le supprimer."
            )
        self.current_data.pop(key, None)

class Workspace:
    """Le gestionnaire central du workspace partagé."""
    def __init__(self):
        self._snapshots: Dict[str, Snapshot] = {}
        initial_snapshot = Snapshot(version_id=str(uuid.uuid4()), data={}, parent_version=None)
        self._snapshots[initial_snapshot.version_id] = initial_snapshot
        self._head_version = initial_snapshot.version_id
        self._events: List[ActRunEvent] = []
        
        # Nouveau : Gestionnaire de leases
        self._lease_manager = LeaseManager()

    @property
    def head(self) -> Snapshot:
        return self._snapshots[self._head_version]

    def create_branch(self, agent_id: str, branch_name: str) -> Branch:
        branch = Branch(
            name=branch_name, 
            base_snapshot=self.head,
            lease_manager=self._lease_manager,
            agent_id=agent_id
        )
        self._events.append(ActRunEvent(
            agent_id=agent_id, action="workspace.branch",
            payload={"branch_name": branch_name, "base_version": self._head_version}
        ))
        return branch

    def commit(self, agent_id: str, branch: Branch) -> Snapshot:
        """Tente de valider les modifications avec détection de conflits."""
        base_snapshot = self._snapshots[branch.base_version]
        
        merge_result = detect_and_merge(
            base_data=base_snapshot.data,
            branch_data=branch.current_data,
            current_head_data=self.head.data
        )
        
        if not merge_result.success:
            raise ConflictError(
                f"Conflit détecté lors du commit de l'agent {agent_id}. "
                f"Les clés suivantes ont été modifiées simultanément : {merge_result.conflicting_keys}",
                conflicting_keys=merge_result.conflicting_keys
            )
        
        new_snapshot = Snapshot(
            version_id=str(uuid.uuid4()),
            data=merge_result.merged_data,
            parent_version=self._head_version
        )
        self._snapshots[new_snapshot.version_id] = new_snapshot
        self._head_version = new_snapshot.version_id
        
        self._events.append(ActRunEvent(
            agent_id=agent_id, action="workspace.commit",
            payload={
                "version_id": new_snapshot.version_id,
                "parent_version": new_snapshot.parent_version,
                "merge_type": "auto-merge" if merge_result.merged_data != branch.current_data else "fast-forward",
                "keys_modified": list(branch.current_data.keys())
            }
        ))
        return new_snapshot

    def acquire_lease(self, agent_id: str, resource_key: str, duration_seconds: float = 30.0) -> Any:
        """Acquiert un verrou sur une ressource."""
        return self._lease_manager.acquire(agent_id, resource_key, duration_seconds)

    def release_lease(self, agent_id: str, resource_key: str) -> None:
        """Libère un verrou sur une ressource."""
        self._lease_manager.release(agent_id, resource_key)

    def get_events(self) -> List[ActRunEvent]:
        """Retourne tous les événements (workspace + leases)."""
        all_events = self._events.copy()
        all_events.extend(self._lease_manager.get_events())
        # Trier par timestamp
        all_events.sort(key=lambda e: e.timestamp)
        return all_events
