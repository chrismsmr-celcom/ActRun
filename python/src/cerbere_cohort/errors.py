# python/src/cerbere_cohort/errors.py
"""Contrat d'erreurs structuré pour Cerbere Cohort.

Chaque erreur de domaine porte :
  - un code machine stable (jamais traduit, jamais reformulé) ;
  - un message humain, en français, inchangé ;
  - des détails structurés JSON (clés en conflit, versions, détenteur...).
La méthode `to_dict()` sérialise le tout pour les couches transport (MCP).
"""
from __future__ import annotations

from typing import Any, Dict, Optional


class CerbereError(Exception):
    """Base commune des erreurs de domaine.

    Les sous-classes fixent leur code par attribut de classe ; `code` peut
    être affiné à la levée (ex : ConflictError -> conflict_detected,
    conflict_unresolved ou conflict_head_moved).
    """

    code: str = "domain_error"

    def __init__(self, message: str = "", *, details: Optional[Dict[str, Any]] = None,
                 code: Optional[str] = None) -> None:
        self.details: Dict[str, Any] = dict(details or {})
        if code is not None:
            self.code = code
        super().__init__(message)

    def to_dict(self) -> Dict[str, Any]:
        """Représentation sérialisable : code stable + message humain + détails."""
        return {"code": self.code, "message": str(self), "details": self.details}
