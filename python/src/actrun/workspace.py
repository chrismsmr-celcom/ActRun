# python/src/actrun/workspace.py
import copy
import uuid
from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from .events import ActRunEvent
from .merge import detect_and_merge, MergeResult, ConflictError

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
    """Le gestionnaire central du workspace partagé."""
    def __init__(self):
        self._snapshots: Dict[str, Snapshot] = {}
        initial_snapshot = Snapshot(version_id=str(uuid.uuid4()), data={}, parent_version=None)
        self._snapshots[initial_snapshot.version_id] = initial_snapshot
        self._head_version = initial_snapshot.version_id
        self._events: List[ActRunEvent] = []

    @property
    def head(self) -> Snapshot:
        return self._snapshots[self._head_version]

    def create_branch(self, agent_id: str, branch_name: str) -> Branch:
        branch = Branch(name=branch_name, base_snapshot=self.head)
        self._events.append(ActRunEvent(
            agent_id=agent_id, action="workspace.branch",
            payload={"branch_name": branch_name, "base_version": self._head_version}
        ))
        return branch

    def commit(self, agent_id: str, branch: Branch) -> Snapshot:
        """
        Tente de valider les modifications. 
        Lève une ConflictError si des clés ont été modifiées en parallèle.
        """
        # 1. Récupérer l'état de base sur lequel la branche a travaillé
        base_snapshot = self._snapshots[branch.base_version]
        
        # 2. Analyser les conflits
        merge_result = detect_and_merge(
            base_data=base_snapshot.data,
            branch_data=branch.current_data,
            current_head_data=self.head.data
        )
        
        if not merge_result.success:
            # Échec : on lève une exception avec les détails
            raise ConflictError(
                f"Conflit détecté lors du commit de l'agent {agent_id}. "
                f"Les clés suivantes ont été modifiées simultanément : {merge_result.conflicting_keys}",
                conflicting_keys=merge_result.conflicting_keys
            )
        
        # 3. Succès : on crée le nouveau snapshot avec les données fusionnées
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

    def get_events(self) -> List[ActRunEvent]:
        return self._events.copy()
