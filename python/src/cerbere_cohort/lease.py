# python/src/cerbere_cohort/lease.py
import time
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Dict, Optional, List
from .events import CerbereCohortEvent
from .errors import CerbereError
from .deadlock import WaitForGraph, DeadlockCycle, DeadlockError

class LeaseError(CerbereError):
    """Exception levée lorsqu'un agent tente de violer l'exclusivité d'un verrou.

    Codes stables selon le point de levée : lease_held, lease_wait_timeout,
    lease_not_owner, lease_required.
    """
    code = "lease_error"

@dataclass
class Lease:
    """Un verrou temporaire sur une ressource."""
    agent_id: str
    resource_key: str
    expires_at: float
    acquired_at: float
    fencing_token: int = 0

    def is_expired(self) -> bool:
        return time.time() > self.expires_at

class LeaseManager:
    """
    Gère les verrous temporaires avec détection de deadlock.
    """
    def __init__(self):
        self._active_leases: Dict[str, Lease] = {}
        self._fencing_counters: Dict[str, int] = {}
        self._events: List[CerbereCohortEvent] = []
        
        # Graphe d'attente pour détecter les deadlocks
        self._wait_for_graph = WaitForGraph()
        
        # File d'attente des agents en attente : resource_key → list d'agents
        self._waiters: Dict[str, List[str]] = {}
        
        # Lock pour la thread-safety (utile si plusieurs agents en parallèle)
        self._lock = threading.RLock()
    
    def acquire(
        self,
        agent_id: str,
        resource_key: str,
        duration_seconds: float = 30.0,
        wait: bool = False,
        timeout_seconds: float = 5.0,
    ) -> Lease:
        """Acquiert un verrou sur une ressource.

        wait=True : attend (jusqu'à timeout_seconds) que la ressource se libère.
        Le verrou interne n'est JAMAIS tenu pendant l'attente, sinon personne
        ne pourrait libérer la ressource ni créer l'arête qui ferme le cycle.

        Raises:
            LeaseError: ressource occupée (wait=False) ou timeout.
            DeadlockError: l'attente fermerait un cycle dans le graphe d'attente.
        """
        deadline = time.monotonic() + timeout_seconds
        try:
            while True:
                with self._lock:
                    self._cleanup_expired()
                    existing = self._active_leases.get(resource_key)

                    if existing is None:
                        return self._create_lease(agent_id, resource_key, duration_seconds)

                    if existing.agent_id == agent_id:
                        existing.expires_at = time.time() + duration_seconds
                        return existing

                    if not wait:
                        raise LeaseError(
                            f"Ressource '{resource_key}' déjà verrouillée par "
                            f"'{existing.agent_id}' jusqu'à {existing.expires_at:.2f}",
                            code="lease_held",
                            details={
                                "resource_key": resource_key,
                                "holder": existing.agent_id,
                                "expires_at": existing.expires_at,
                            },
                        )

                    # (re)déclare l'attente : le détenteur a pu changer entre deux tours
                    self._wait_for_graph.remove_wait(agent_id)
                    self._wait_for_graph.add_wait(agent_id, existing.agent_id, resource_key)
                    cycle = self._wait_for_graph.detect_cycle()
                    if cycle:
                        raise DeadlockError(
                            f"Deadlock détecté : {cycle}",
                            details={
                                "cycle": list(cycle.cycle),
                                "resources": list(cycle.resources),
                            },
                        )

                    if time.monotonic() >= deadline:
                        raise LeaseError(
                            f"Timeout après {timeout_seconds}s en attendant "
                            f"'{resource_key}' (détenu par '{existing.agent_id}')",
                            code="lease_wait_timeout",
                            details={
                                "resource_key": resource_key,
                                "holder": existing.agent_id,
                                "timeout_seconds": timeout_seconds,
                            },
                        )
                time.sleep(0.02)  # verrou relâché pendant la pause
        finally:
            if wait:
                with self._lock:
                    self._wait_for_graph.remove_wait(agent_id)

    @contextmanager
    def fencing_guard(self):
        """Hold lease ownership stable while a workspace validates and commits writes."""
        with self._lock:
            yield

    def _create_lease(self, agent_id: str, resource_key: str, duration_seconds: float) -> Lease:
        """Crée et enregistre un nouveau lease."""
        now = time.time()
        token = self._fencing_counters.get(resource_key, 0) + 1
        self._fencing_counters[resource_key] = token
        lease = Lease(
            agent_id=agent_id,
            resource_key=resource_key,
            expires_at=now + duration_seconds,
            acquired_at=now,
            fencing_token=token,
        )
        self._active_leases[resource_key] = lease
        
        self._events.append(CerbereCohortEvent(
            agent_id=agent_id,
            action="lease.acquire",
            payload={
                "resource_key": resource_key,
                "duration_seconds": duration_seconds,
                "expires_at": lease.expires_at,
                "fencing_token": lease.fencing_token,
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
                    f"'{resource_key}' détenu par '{lease.agent_id}'",
                    code="lease_not_owner",
                    details={
                        "agent_id": agent_id,
                        "resource_key": resource_key,
                        "holder": lease.agent_id,
                    },
                )
            
            del self._active_leases[resource_key]
            
            self._events.append(CerbereCohortEvent(
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
    
    def get_events(self) -> List[CerbereCohortEvent]:
        return self._events.copy()
