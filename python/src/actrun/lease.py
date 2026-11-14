# python/src/actrun/lease.py
import time
from dataclasses import dataclass
from typing import Dict, Optional, Set
from .events import ActRunEvent

class LeaseError(Exception):
    """Exception levée lorsqu'un agent tente d'acquérir une ressource déjà verrouillée."""
    pass

class DeadlockError(Exception):
    """Exception levée lorsqu'un cycle de dépendances est détecté."""
    pass

@dataclass
class Lease:
    """Un verrou temporaire sur une ressource."""
    agent_id: str
    resource_key: str
    expires_at: float  # Timestamp UNIX (time.time())
    acquired_at: float

    def is_expired(self) -> bool:
        return time.time() > self.expires_at

class LeaseManager:
    """
    Gère les verrous temporaires sur les ressources du workspace.
    Empêche les conflits AVANT qu'ils ne se produisent.
    """
    def __init__(self):
        # Clé : resource_key, Valeur : Lease actif
        self._active_leases: Dict[str, Lease] = {}
        
        # Journal des événements de leases
        self._events: list[ActRunEvent] = []

    def acquire(
        self, 
        agent_id: str, 
        resource_key: str, 
        duration_seconds: float = 30.0
    ) -> Lease:
        """
        Tente d'acquérir un verrou sur une ressource.
        
        Args:
            agent_id: L'agent qui demande le verrou
            resource_key: La clé/ressource à verrouiller
            duration_seconds: Durée du verrou en secondes (défaut: 30s)
        
        Returns:
            Lease: Le verrou acquis
        
        Raises:
            LeaseError: Si la ressource est déjà verrouillée par un autre agent
        """
        # 1. Nettoyer les verrous expirés
        self._cleanup_expired()
        
        # 2. Vérifier si la ressource est déjà verrouillée
        if resource_key in self._active_leases:
            existing_lease = self._active_leases[resource_key]
            if existing_lease.agent_id != agent_id:
                raise LeaseError(
                    f"Ressource '{resource_key}' déjà verrouillée par l'agent "
                    f"'{existing_lease.agent_id}' jusqu'à {existing_lease.expires_at}"
                )
            # Si c'est le même agent, on peut étendre le verrou (renew)
        
        # 3. Créer le nouveau verrou
        now = time.time()
        lease = Lease(
            agent_id=agent_id,
            resource_key=resource_key,
            expires_at=now + duration_seconds,
            acquired_at=now
        )
        
        self._active_leases[resource_key] = lease
        
        # 4. Enregistrer l'événement
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
        """
        Libère volontairement un verrou.
        
        Raises:
            LeaseError: Si l'agent ne possède pas le verrou
        """
        if resource_key not in self._active_leases:
            return  # Déjà libéré ou jamais acquis
        
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
        """
        Vérifie si un agent possède un verrou actif sur une ressource.
        """
        self._cleanup_expired()
        
        if resource_key not in self._active_leases:
            return False
        
        return self._active_leases[resource_key].agent_id == agent_id

    def get_active_leases(self) -> Dict[str, Lease]:
        """Retourne tous les verrous actifs (après nettoyage des expirés)."""
        self._cleanup_expired()
        return self._active_leases.copy()

    def _cleanup_expired(self) -> None:
        """Supprime tous les verrous expirés."""
        expired_keys = [
            key for key, lease in self._active_leases.items() 
            if lease.is_expired()
        ]
        for key in expired_keys:
            del self._active_leases[key]

    def get_events(self) -> list[ActRunEvent]:
        return self._events.copy()
