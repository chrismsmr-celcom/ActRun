"""
Détection de deadlock via Wait-for Graph.

Un deadlock se produit quand un cycle existe dans le graphe d'attente :
  Agent A attend Agent B, qui attend Agent C, qui attend Agent A → cycle !

Algorithme : DFS avec détection de cycle (coloration).
"""
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass


class DeadlockError(Exception):
    """Levée quand une attente créerait un cycle (deadlock)."""


@dataclass
class DeadlockCycle:
    """Représente un cycle de deadlock détecté."""
    cycle: List[str]  # Liste des agent_id dans l'ordre du cycle
    resources: List[str]  # Ressources impliquées (même taille que cycle)
    
    def __str__(self) -> str:
        parts = []
        for i, agent in enumerate(self.cycle):
            resource = self.resources[i]
            next_agent = self.cycle[(i + 1) % len(self.cycle)]
            parts.append(f"{agent} attend '{resource}' détenu par {next_agent}")
        return " → ".join(parts)


class WaitForGraph:
    """
    Graphe d'attente : arêtes agent → agent.
    Une arête A → B signifie "A attend une ressource détenue par B".
    """
    def __init__(self):
        # agent_id → set d'agents qu'il attend
        self._edges: Dict[str, Set[str]] = {}
        # (agent_waiter, agent_holder) → resource_key
        self._resources: Dict[Tuple[str, str], str] = {}
    
    def add_wait(self, waiter: str, holder: str, resource_key: str) -> None:
        """Ajoute une arête : waiter attend holder pour resource_key."""
        if waiter not in self._edges:
            self._edges[waiter] = set()
        self._edges[waiter].add(holder)
        self._resources[(waiter, holder)] = resource_key
    
    def remove_wait(self, waiter: str) -> None:
        """Supprime toutes les attentes d'un agent (quand il n'attend plus)."""
        if waiter in self._edges:
            # Nettoyer les ressources associées
            for holder in list(self._edges[waiter]):
                self._resources.pop((waiter, holder), None)
            del self._edges[waiter]
    
    def detect_cycle(self) -> DeadlockCycle | None:
        """
        Détecte un cycle dans le graphe via DFS.
        Retourne le premier cycle trouvé, ou None.
        """
        # État de chaque nœud : 0 = blanc (non visité), 1 = gris (en cours), 2 = noir (fini)
        color: Dict[str, int] = {node: 0 for node in self._edges}
        parent: Dict[str, str | None] = {}
        
        def dfs(node: str, path: List[str]) -> DeadlockCycle | None:
            color[node] = 1  # Gris
            path.append(node)
            
            for neighbor in self._edges.get(node, set()):
                if color.get(neighbor, 0) == 1:
                    # Cycle détecté ! Extraire le cycle depuis path
                    cycle_start = path.index(neighbor)
                    cycle_agents = path[cycle_start:]
                    
                    # Construire la liste des ressources
                    cycle_resources = []
                    for i in range(len(cycle_agents)):
                        current = cycle_agents[i]
                        next_agent = cycle_agents[(i + 1) % len(cycle_agents)]
                        resource = self._resources.get((current, next_agent), "?")
                        cycle_resources.append(resource)
                    
                    return DeadlockCycle(cycle=cycle_agents, resources=cycle_resources)
                
                elif color.get(neighbor, 0) == 0:
                    parent[neighbor] = node
                    result = dfs(neighbor, path)
                    if result:
                        return result
            
            path.pop()
            color[node] = 2  # Noir
            return None
        
        for node in list(self._edges.keys()):
            if color[node] == 0:
                result = dfs(node, [])
                if result:
                    return result
        
        return None
    
    def __repr__(self) -> str:
        lines = ["WaitForGraph:"]
        for waiter, holders in self._edges.items():
            for holder in holders:
                resource = self._resources.get((waiter, holder), "?")
                lines.append(f"  {waiter} --[{resource}]--> {holder}")
        return "\n".join(lines) if len(lines) > 1 else "WaitForGraph: (vide)"
