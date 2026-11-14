# python/src/actrun/merge.py
from typing import Dict, Any, List
from dataclasses import dataclass

class ConflictError(Exception):
    """Exception levée lorsque des modifications concurrentes sont détectées sur les mêmes clés."""
    def __init__(self, message: str, conflicting_keys: List[str]):
        super().__init__(message)
        self.conflicting_keys = conflicting_keys

@dataclass
class MergeResult:
    """Résultat de la tentative de fusion."""
    success: bool
    merged_data: Dict[str, Any] = None
    conflicting_keys: List[str] = None

def detect_and_merge(base_data: Dict[str, Any], branch_data: Dict[str, Any], current_head_data: Dict[str, Any]) -> MergeResult:
    """
    Compare les modifications de la branche avec celles du HEAD actuel par rapport à la base.
    
    - Si aucune clé modifiée ne se chevauche : Fusion automatique (Auto-merge).
    - Si des clés se chevauchent : Échec avec liste des clés en conflit.
    """
    # 1. Identifier ce que la branche a modifié par rapport à la base
    branch_changes = {
        k: v for k, v in branch_data.items() if base_data.get(k) != v
    }
    
    # 2. Identifier ce que le HEAD a modifié par rapport à la base (pendant que la branche travaillait)
    head_changes = {
        k: v for k, v in current_head_data.items() if base_data.get(k) != v
    }
    
    # 3. Trouver l'intersection (les clés modifiées par les deux)
    conflicting_keys = list(set(branch_changes.keys()) & set(head_changes.keys()))
    
    if conflicting_keys:
        # CONFLIT DÉTECTÉ
        return MergeResult(
            success=False, 
            conflicting_keys=conflicting_keys
        )
    
    # PAS DE CONFLIT : On peut fusionner en toute sécurité
    # On part du HEAD actuel et on y applique les changements de la branche
    merged_data = current_head_data.copy()
    merged_data.update(branch_changes)
    
    return MergeResult(
        success=True, 
        merged_data=merged_data
    )
