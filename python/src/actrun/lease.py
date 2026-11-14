# python/src/actrun/lease.py
import time
import threading
from dataclasses import dataclass
from typing import Dict, Optional, List
from .events import ActRunEvent
from .deadlock import WaitForGraph, DeadlockCycle, DeadlockError

class LeaseError(Exception):
    """Exception levée lorsqu'un agent tente d'acquérir une ressource déjà verrouillée."""
    pass

@dataclass
class Lease:
    """Un verrou temporaire sur une ressource."""
    agent_id: str
    resource_key: str
    expires_at: float
    acquired_at: float

    def is_expired(self) -> bool:
        return time.time() > self.expires_at

class LeaseManager:
    """
    Gère les verrous temporaires avec détection de deadlock.
    """
    def __init__(self):
        self._active_leases: Dict[str, Lease] = {}
        self._events: List[ActRunEvent] = []
        
        # Graphe d'attente pour détecter les deadlocks
        self._wait_for_graph = WaitForGraph()
        
        # File d'attente des agents en attente : resource_key → list d'agents
        self._waiters: Dict[str, List[str]] = {}
        
        # Lock pour la thread-safety (utile si plusieurs agents en parallèle)
        self._lock = threading.Lock()
    
    def acquire(
        self,
        agent_id: str,
        resource_key: str,
        duration_seconds: float = 30.0,
        wait: bool = False,
        timeout_seconds: float = 5.0
    ) -> Lease:
        """
        Acquiert un verrou sur une ressource.
        
        Args:
            agent_id: L'agent qui demande le verrou
            resource_key: La ressource à verrouiller
            duration_seconds: Durée du verrou
            wait: Si True, attend que la ressource se libère (avec détection de deadlock)
            timeout_seconds: Timeout d'attente si wait=True
        
        Raises:
            LeaseError: Si la ressource est déjà verrouillée et wait=False
            DeadlockError: Si l'attente créerait un cycle de deadlock
        """
        with self._lock:
            self._cleanup_expired()
            
            # Cas 1 : Ressource libre → acquérir immédiatement
            if resource_key not in self._active_leases:
                return self._create_lease(agent_id, resource_key, duration_seconds)
            
            existing = self._active_leases[resource_key]
            
            # Cas 2 : Même agent → renouveler le lease
            if existing.agent_id == agent_id:
                existing.expires_at = time.time() + duration_seconds
                return existing
            
            # Cas 3 : Ressource occupée par un autre agent
            if not wait:
                raise LeaseError(
                    f"Ressource '{resource_key}' déjà verrouillée par '{existing.agent_id}' "
                    f"jusqu'à {existing.expires_at:.2f}"
                )
            
            # Cas 4 : Mode attente → vérifier les deadlocks
            return self._acquire_with_wait(
                agent_id, resource_key, duration_seconds, timeout_seconds
            )
    
    def _acquire_with_wait(
        self,
        agent_id: str,
        resource_key: str,
        duration_seconds: float,
        timeout_seconds: float
    ) -> Lease:
        """Acquiert avec attente et détection de deadlock."""
        holder = self._active_leases[resource_key].agent_id
        
        # 1. Ajouter l'attente au graphe
        self._wait_for_graph.add_wait(agent_id, holder, resource_key)
        
        # 2. DÉTECTION DE DEADLOCK : vérifier si un cycle existe
        cycle = self._wait_for_graph.detect_cycle()
        if cycle:
            # Nettoyer avant de lever l'exception
            self._wait_for_graph.remove_wait(agent_id)
            raise DeadlockError(
                f"DEADLOCK DÉTECTÉ ! Cycle : {cycle}"
            )
        
        # 3. Pas de deadlock → attendre avec timeout
        start_time = time.time()
        while time.time() - start_time < timeout_seconds:
            self._cleanup_expired()
            
            # La ressource s'est libérée ?
            if resource_key not in self._active_leases:
                self._wait_for_graph.remove_wait(agent_id)
                return self._create_lease(agent_id, resource_key, duration_seconds)
            
            # Petite pause pour ne pas saturer le CPU
            time.sleep(0.05)
        
        # Timeout atteint
        self._wait_for_graph.remove_wait(agent_id)
        raise LeaseError(
            f"Timeout après {timeout_seconds}s en attendant '{resource_key}' "
            f"(détenu par '{holder}')"
        )
    
    def _create_lease(self, agent_id: str, resource_key: str, duration_seconds: float) -> Lease:
        """Crée et enregistre un nouveau lease."""
        now = time.time()
        lease = Lease(
            agent_id=agent_id,
            resource_key=resource_key,
            expires_at=now + duration_seconds,
            acquired_at=now
        )
        self._active_leases[resource_key] = lease
        
        self._events.append(ActRunEvent(
            agent_id=agent_id,
            action="lease.acquire",
            payload={
                "resource_key": resource_key,
                "duration_seconds": duration_seconds,
                "expires_at": lease.expires_at
            }
        ))
        return lease
    
    def release(self, agent_id: str, resource_key: str) -> None:
        """Libère un verrou."""
        with self._lock:
            if resource_key not in self._active_leases:
                return
            
            lease = self._active_leases[resource_key]
            if lease.agent_id != agent_id:
                raise LeaseError(
                    f"L'agent '{agent_id}' ne peut pas libérer le verrou de "
                    f"'{resource_key}' détenu par '{lease.agent_id}'"
                )
            
            del self._active_leases[resource_key]
            
            self._events.append(ActRunEvent(
                agent_id=agent_id,
                action="lease.release",
                payload={"resource_key": resource_key}
            ))
    
    def check_lease(self, agent_id: str, resource_key: str) -> bool:
        """Vérifie si un agent possède un lease actif."""
        with self._lock:
            self._cleanup_expired()
            if resource_key not in self._active_leases:
                return False
            return self._active_leases[resource_key].agent_id == agent_id
    
    def get_active_leases(self) -> Dict[str, Lease]:
        with self._lock:
            self._cleanup_expired()
            return self._active_leases.copy()
    
    def _cleanup_expired(self) -> None:
        """Supprime les leases expirés."""
        expired = [k for k, v in self._active_leases.items() if v.is_expired()]
        for k in expired:
            del self._active_leases[k]
    
    def get_events(self) -> List[ActRunEvent]:
        return self._events.copy()
