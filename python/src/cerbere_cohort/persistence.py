"""
Persistance SQLite pour Cerbere Cohort.

Sauvegarde l'état du workspace (snapshots, événements, leases) sur disque.
Permet la reprise après arrêt et le replay déterministe.
"""
import json
import sqlite3
import threading
from pathlib import Path
from typing import Optional, List, Dict, Any

from .events import CerbereCohortEvent
from .workspace import Workspace, Snapshot, Branch, ContentStore
from .lease import LeaseManager, Lease


class PersistentWorkspace:
    """
    Workspace persistant basé sur SQLite.
    
    Sauvegarde automatiquement :
    - Les snapshots (états du workspace)
    - Les événements (journal immuable)
    - Les leases actifs (verrous)
    """
    
    def __init__(self, db_path: str | Path, auto_save: bool = True):
        """
        Args:
            db_path: Chemin vers le fichier SQLite
            auto_save: Si True, sauvegarde automatiquement à chaque opération
        """
        self.db_path = Path(db_path)
        self.auto_save = auto_save
        self._lock = threading.Lock()
        
        # Workspace en mémoire : reconstruit par replay du journal au chargement
        self._workspace = Workspace()
        self._persisted_ids: set[str] = set()
        self._persisted_hashes: set[str] = set()
        
        # Connexion SQLite
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        
        # Activer le mode WAL pour de meilleures performances
        self._conn.execute("PRAGMA journal_mode=WAL")
        
        # Initialiser le schéma
        self._init_schema()
        
        # Charger l'état existant si présent
        self._load_from_db()
    
    def _init_schema(self):
        """Crée les tables SQLite si elles n'existent pas."""
        with self._lock:
            self._conn.executescript("""
                CREATE TABLE IF NOT EXISTS objects (
                    hash TEXT PRIMARY KEY,
                    content TEXT NOT NULL
                );
                
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    metadata_json TEXT
                );
                
                CREATE TABLE IF NOT EXISTS leases (
                    resource_key TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    expires_at REAL NOT NULL,
                    acquired_at REAL NOT NULL
                );
                
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                
                CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
                CREATE INDEX IF NOT EXISTS idx_events_agent ON events(agent_id);
                CREATE INDEX IF NOT EXISTS idx_events_action ON events(action);
            """)
            self._conn.commit()
    
    def _load_from_db(self):
        """Reconstruit le workspace par REPLAY du journal (les ids sont vérifiés)."""
        with self._lock:
            store = ContentStore()
            for r in self._conn.execute("SELECT hash, content FROM objects"):
                store.load_text(r['hash'], r['content'])
                self._persisted_hashes.add(r['hash'])

            events = []
            for r in self._conn.execute(
                "SELECT event_id, timestamp, agent_id, action, payload_json, metadata_json FROM events ORDER BY rowid"
            ):
                events.append(CerbereCohortEvent(
                    event_id=r['event_id'],
                    timestamp=r['timestamp'],
                    agent_id=r['agent_id'],
                    action=r['action'],
                    payload=json.loads(r['payload_json']),
                    metadata=json.loads(r['metadata_json']) if r['metadata_json'] else None
                ))
                self._persisted_ids.add(r['event_id'])

            self._workspace = Workspace.replay(events, store)  # lève ReplayError si le journal est incohérent
            
            # Charger les leases actifs
            cursor = self._conn.execute(
                "SELECT resource_key, agent_id, expires_at, acquired_at FROM leases"
            )
            for r in cursor:
                lease = Lease(
                    agent_id=r['agent_id'],
                    resource_key=r['resource_key'],
                    expires_at=r['expires_at'],
                    acquired_at=r['acquired_at']
                )
                self._workspace._lease_manager._active_leases[r['resource_key']] = lease
    
    # === API publique (délègue au workspace + persiste) ===
    
    @property
    def head(self) -> Snapshot:
        return self._workspace.head
    
    def create_branch(self, agent_id: str, branch_name: str) -> Branch:
        """Crée une branche et la persiste."""
        branch = self._workspace.create_branch(agent_id, branch_name)
        if self.auto_save:
            self._save_new_events()
        return branch
    
    def commit(self, agent_id: str, branch: Branch, resolver=None, max_retries: int = 3) -> Snapshot:
        """Committe et persiste le nouveau snapshot."""
        try:
            snapshot = self._workspace.commit(agent_id, branch, resolver=resolver, max_retries=max_retries)
        finally:
            # le conflit est aussi un événement : on le persiste même si commit lève
            if self.auto_save:
                self._save_new_objects()
                self._save_new_events()
        return snapshot

    def seed(self, data: Dict[str, Any], agent_id: str = "system") -> Snapshot:
        """Initialise l'état par un commit journalisé et persisté."""
        snapshot = self._workspace.seed(data, agent_id)
        if self.auto_save:
            self._save_new_objects()
            self._save_new_events()
        return snapshot

    @property
    def store(self) -> ContentStore:
        return self._workspace.store
    
    def acquire_lease(self, agent_id: str, resource_key: str, duration_seconds: float = 30.0, **kwargs) -> Lease:
        """Acquiert un lease et le persiste."""
        lease = self._workspace.acquire_lease(agent_id, resource_key, duration_seconds, **kwargs)
        if self.auto_save:
            self._save_lease(lease)
            self._save_new_events()
        return lease
    
    def release_lease(self, agent_id: str, resource_key: str) -> None:
        """Libère un lease et le persiste."""
        self._workspace.release_lease(agent_id, resource_key)
        if self.auto_save:
            self._delete_lease(resource_key)
            self._save_new_events()
    
    def get_events(self) -> List[CerbereCohortEvent]:
        return self._workspace.get_events()
    
    # === Méthodes de persistance ===
    
    def _save_new_objects(self):
        """Persiste les contenus pas encore écrits. Toujours AVANT les événements qui les référencent."""
        objects = self._workspace.store.dump()
        with self._lock:
            for digest, text in objects.items():
                if digest not in self._persisted_hashes:
                    self._conn.execute("INSERT OR IGNORE INTO objects (hash, content) VALUES (?, ?)", (digest, text))
                    self._persisted_hashes.add(digest)
            self._conn.commit()
    
    def _save_lease(self, lease: Lease):
        """Sauvegarde un lease dans SQLite."""
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO leases (resource_key, agent_id, expires_at, acquired_at) VALUES (?, ?, ?, ?)",
                (lease.resource_key, lease.agent_id, lease.expires_at, lease.acquired_at)
            )
            self._conn.commit()
    
    def _delete_lease(self, resource_key: str):
        """Supprime un lease de SQLite."""
        with self._lock:
            self._conn.execute("DELETE FROM leases WHERE resource_key = ?", (resource_key,))
            self._conn.commit()
    
    def _save_new_events(self):
        """Persiste tous les événements pas encore écrits (workspace ET leases)."""
        events = self._workspace.get_events()
        with self._lock:
            for event in events:
                if event.event_id in self._persisted_ids:
                    continue
                self._conn.execute(
                    "INSERT OR IGNORE INTO events (event_id, timestamp, agent_id, action, payload_json, metadata_json) VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        event.event_id,
                        event.timestamp,
                        event.agent_id,
                        event.action,
                        json.dumps(event.payload, ensure_ascii=False),
                        json.dumps(event.metadata, ensure_ascii=False) if event.metadata else None,
                    ),
                )
                self._persisted_ids.add(event.event_id)
            self._conn.commit()

    # === Méthodes utilitaires ===
    
    def get_snapshot_count(self) -> int:
        """Retourne le nombre total de snapshots."""
        return len(self._workspace._snapshots)
    
    def get_event_count(self) -> int:
        """Retourne le nombre total d'événements."""
        with self._lock:
            cursor = self._conn.execute("SELECT COUNT(*) FROM events")
            return cursor.fetchone()[0]
    
    def get_active_lease_count(self) -> int:
        """Retourne le nombre de leases actifs."""
        with self._lock:
            cursor = self._conn.execute("SELECT COUNT(*) FROM leases")
            return cursor.fetchone()[0]
    
    def export_events_jsonl(self, output_path: str | Path) -> int:
        """
        Exporte tous les événements au format JSONL.
        Compatible avec le moteur de trace Rust.
        
        Returns:
            Nombre d'événements exportés
        """
        output_path = Path(output_path)
        count = 0
        
        with self._lock:
            cursor = self._conn.execute(
                "SELECT event_id, timestamp, agent_id, action, payload_json, metadata_json FROM events ORDER BY rowid"
            )
            
            with open(output_path, 'w', encoding='utf-8') as f:
                for row in cursor:
                    event = CerbereCohortEvent(
                        event_id=row['event_id'],
                        timestamp=row['timestamp'],
                        agent_id=row['agent_id'],
                        action=row['action'],
                        payload=json.loads(row['payload_json']),
                        metadata=json.loads(row['metadata_json']) if row['metadata_json'] else None
                    )
                    f.write(event.to_jsonl() + '\n')
                    count += 1
        
        return count
    
    def close(self):
        """Ferme la connexion SQLite."""
        with self._lock:
            self._conn.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
