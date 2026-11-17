# python/src/cerbere_cohort/resolve.py
"""Résolution des conflits (docs/CONCEPTS.md §5).

Un résolveur reçoit un `Conflict` et renvoie une `Resolution` ou None (« non résolu »).
Il peut être non déterministe (humain, modèle) : seule sa DÉCISION est enregistrée
(événement `coordination.resolved`) et le replay applique la décision enregistrée,
sans jamais rappeler le résolveur.
"""
from dataclasses import dataclass
from typing import Any, Callable, Optional, Sequence

from .errors import CerbereError


class ResolutionError(CerbereError):
    """Le résolveur a levé une exception ou rendu une décision invalide."""
    code = "resolution_error"


@dataclass(frozen=True)
class Side:
    """Une version concurrente d'une clé."""
    present: bool                     # False = la clé est absente / supprimée de ce côté
    hash: Optional[str] = None        # hash de contenu (None si absente)
    value: Any = None                 # copie fraîche de la valeur (None si absente)
    agent_id: Optional[str] = None    # qui a écrit cette version (None pour la base)
    intent: Optional[str] = None      # pourquoi (métadonnée : n'influence jamais la détection)


@dataclass(frozen=True)
class Conflict:
    key: str
    base: Side      # version commune de départ
    ours: Side      # la branche qui commit
    theirs: Side    # le HEAD courant (déjà commité par quelqu'un d'autre)


@dataclass(frozen=True)
class Resolution:
    present: bool                  # False = supprimer la clé
    value: Any = None
    rationale: str = ""

    @staticmethod
    def take(side: Side, rationale: str = "") -> "Resolution":
        """Retient une des versions (ou sa suppression si la clé y est absente)."""
        return Resolution(present=side.present, value=side.value if side.present else None, rationale=rationale)

    @staticmethod
    def delete(rationale: str = "") -> "Resolution":
        return Resolution(present=False, rationale=rationale)

    @staticmethod
    def with_value(value: Any, rationale: str = "") -> "Resolution":
        """Contenu nouveau, par exemple une fusion produite par un arbitre."""
        return Resolution(present=True, value=value, rationale=rationale)


class Resolver:
    """Interface : surcharger `resolve`. `name` est enregistré dans le journal."""
    name = "resolver"

    def resolve(self, conflict: Conflict) -> Optional[Resolution]:
        raise NotImplementedError

    def __call__(self, conflict: Conflict) -> Optional[Resolution]:
        return self.resolve(conflict)


class PreferBranch(Resolver):
    """La branche qui commit l'emporte (dernier écrivain gagnant)."""
    name = "prefer-branch"

    def resolve(self, conflict):
        return Resolution.take(conflict.ours, "la branche qui commit l'emporte")


class PreferHead(Resolver):
    """Le HEAD déjà commité est conservé (premier arrivé gagnant)."""
    name = "prefer-head"

    def resolve(self, conflict):
        return Resolution.take(conflict.theirs, "le HEAD déjà commité est conservé")


class PreferAgent(Resolver):
    """L'agent le plus prioritaire (premier de la liste) l'emporte. Égalité ou inconnus : non résolu."""

    def __init__(self, priority: Sequence[str]):
        self._rank = {agent: i for i, agent in enumerate(priority)}
        self.name = f"prefer-agent({','.join(priority)})"

    def resolve(self, conflict):
        ours = self._rank.get(conflict.ours.agent_id)
        theirs = self._rank.get(conflict.theirs.agent_id)
        if ours is None and theirs is None or ours == theirs:
            return None
        if theirs is None or (ours is not None and ours < theirs):
            return Resolution.take(conflict.ours, f"priorité à l'agent '{conflict.ours.agent_id}'")
        return Resolution.take(conflict.theirs, f"priorité à l'agent '{conflict.theirs.agent_id}'")


class CallbackResolver(Resolver):
    """Enveloppe une fonction (humain, modèle, règle métier) : Conflict -> Resolution | None."""

    def __init__(self, fn: Callable[[Conflict], Optional[Resolution]], name: str = "callback"):
        self._fn = fn
        self.name = name

    def resolve(self, conflict):
        return self._fn(conflict)


class ResolverChain(Resolver):
    """Essaie les résolveurs dans l'ordre ; le premier qui décide l'emporte."""

    def __init__(self, *resolvers: Resolver):
        self._resolvers = resolvers
        self.name = "chain(" + ",".join(r.name for r in resolvers) + ")"

    def resolve(self, conflict):
        for resolver in self._resolvers:
            decision = resolver.resolve(conflict)
            if decision is not None:
                return decision
        return None
