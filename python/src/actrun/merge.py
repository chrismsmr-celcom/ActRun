# python/src/actrun/merge.py
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

_ABSENT = object()  # distingue "clé absente" de "valeur None"


class ConflictError(Exception):
    """Levée lorsque des modifications concurrentes divergent sur les mêmes clés."""

    def __init__(self, message: str, conflicting_keys: List[str]):
        super().__init__(message)
        self.conflicting_keys = conflicting_keys


@dataclass
class MergeResult:
    success: bool
    merged_data: Optional[Dict[str, Any]] = None
    conflicting_keys: Optional[List[str]] = None


def detect_and_merge(
    base_data: Dict[str, Any],
    branch_data: Dict[str, Any],
    current_head_data: Dict[str, Any],
) -> MergeResult:
    """Fusion à trois voies, clé par clé (règle de CONCEPTS.md §4).

    Pour chaque clé, avec M = valeur dans la base ("absente" comprise) :
      - la branche n'a pas changé la clé          -> on garde le HEAD
      - le HEAD n'a pas changé la clé             -> on prend la branche
      - branche et HEAD ont changé vers la même valeur -> pas de conflit
      - sinon (y compris suppression vs modification)  -> CONFLIT
    """
    merged = dict(current_head_data)
    conflicts: List[str] = []

    for key in set(base_data) | set(branch_data) | set(current_head_data):
        base = base_data.get(key, _ABSENT)
        mine = branch_data.get(key, _ABSENT)
        head = current_head_data.get(key, _ABSENT)

        if mine == base:
            continue  # la branche n'a rien changé ici
        if head == base or head == mine:
            if mine is _ABSENT:
                merged.pop(key, None)
            else:
                merged[key] = mine
        else:
            conflicts.append(key)

    if conflicts:
        # merged_data = fusion des clés SANS conflit ; les clés en conflit gardent la valeur du HEAD
        return MergeResult(success=False, merged_data=merged, conflicting_keys=sorted(conflicts))
    return MergeResult(success=True, merged_data=merged)
