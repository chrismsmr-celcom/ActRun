# python/src/cerbere_cohort/hashing.py
"""Identité par le contenu : JSON canonique, SHA-256, ids de snapshot.

Règle (docs/CONCEPTS.md §3) : l'identité d'un document est le SHA-256 de son
contenu ; l'id d'un snapshot dérive du mapping ET des ids de ses parents.
Même contenu + même historique => même id, sur n'importe quelle machine.
"""
import hashlib
import json
import math
from typing import Any, Mapping, Sequence

from .errors import CerbereError


class ContentError(CerbereError, ValueError):
    """La valeur ne peut pas être représentée de façon canonique (non JSON, NaN, clé non-str...)."""
    code = "content_invalid_value"


def _validate(value: Any, path: str = "$") -> None:
    if value is None or isinstance(value, (bool, str, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ContentError(f"{path}: NaN et Infinity ne sont pas hachables")
        return
    if isinstance(value, list):
        for i, item in enumerate(value):
            _validate(item, f"{path}[{i}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ContentError(f"{path}: les clés d'objet doivent être des str (reçu {type(key).__name__})")
            _validate(item, f"{path}.{key}")
        return
    raise ContentError(
        f"{path}: {type(value).__name__} n'est pas sérialisable "
        "(types admis : null, bool, int, float, str, list, dict)"
    )


def canonical_json(value: Any) -> str:
    """JSON canonique : clés triées, sans espaces, UTF-8 non échappé."""
    try:
        _validate(value)
        return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    except RecursionError:
        raise ContentError("valeur trop imbriquée ou auto-référencée") from None


def hash_text(text: str) -> str:
    try:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()
    except UnicodeEncodeError:
        raise ContentError("chaîne non encodable en UTF-8 (surrogate isolé ?)") from None


def content_hash(value: Any) -> str:
    """SHA-256 (hex) du JSON canonique de `value`."""
    return hash_text(canonical_json(value))


def snapshot_id(entries: Mapping[str, str], parents: Sequence[str]) -> str:
    """Id d'un snapshot = H(entrées triées + parents ordonnés).

    L'ordre des parents compte : le premier est la tête cible au moment du commit.
    """
    body = json.dumps(
        {"entries": dict(sorted(entries.items())), "parents": list(parents)},
        sort_keys=True, ensure_ascii=False, separators=(",", ":"),
    )
    return hash_text("actrun.snapshot.v1\n" + body)
