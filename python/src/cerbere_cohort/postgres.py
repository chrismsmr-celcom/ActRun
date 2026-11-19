"""PostgreSQL persistence backend for Cohort.

Uses the same replay-verified event model as PersistentWorkspace. A transaction-
scoped advisory lock serializes workspace mutations across API instances.
"""
from __future__ import annotations

import re
import threading
from typing import Any

from .persistence import PersistentWorkspace
from .lease import Lease


class _HybridRow(dict):
    """Mapping row compatible with sqlite3.Row's integer indexing."""
    def __getitem__(self, key):
        if isinstance(key, int):
            return tuple(self.values())[key]
        return super().__getitem__(key)


def _row_factory(cursor):
    names = [column.name for column in cursor.description]
    return _HybridRow(zip(names, row) for row in cursor)


class _PostgresConnection:
    """Small DB-API compatibility layer for the existing persistence engine."""
    def __init__(self, dsn: str):
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:
            raise RuntimeError(
                "PostgreSQL support requires psycopg[binary]>=3.2. "
                "Install the production dependencies."
            ) from exc
        self._conn = psycopg.connect(dsn, row_factory=dict_row, connect_timeout=15)

    @staticmethod
    def _sql(statement: str) -> str:
        sql = statement.strip()
        if sql.upper() == "BEGIN IMMEDIATE":
            return "BEGIN"
        sql = re.sub(r"^INSERT\\s+OR\\s+IGNORE\\s+INTO", "INSERT INTO", sql, flags=re.I)
        sql = sql.replace("?", "%s")
        sql = re.sub(r"ORDER\\s+BY\\s+rowid", "ORDER BY seq", sql, flags=re.I)
        if re.match(r"^INSERT INTO", sql, flags=re.I) and "ON CONFLICT" not in sql.upper():
            sql = sql.rstrip().rstrip(";") + " ON CONFLICT DO NOTHING"
        return sql

    def execute(self, statement: str, parameters=()):
        sql = self._sql(statement)
        cursor = self._conn.execute(sql, parameters)
        if statement.strip().upper() == "BEGIN IMMEDIATE":
            # All writers for this logical workspace serialize across processes.
            self._conn.execute(
                "SELECT pg_advisory_xact_lock(hashtext('cerbere-cohort-runtime'))"
            )
        return cursor

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()


class PostgresPersistentWorkspace(PersistentWorkspace):
    """PostgreSQL-backed implementation of PersistentWorkspace.

    DATABASE_URL must be a PostgreSQL connection string. Schema migrations are
    additive and safe to run at process startup.
    """
    def __init__(self, database_url: str, auto_save: bool = True, require_leases: bool = False):
        if not database_url.startswith(("postgres://", "postgresql://")):
            raise ValueError("DATABASE_URL must use postgres:// or postgresql://")
        self.db_path = database_url
        self.auto_save = auto_save
        self.require_leases = require_leases
        self._lock = threading.RLock()
        from .workspace import Workspace
        self._workspace = Workspace(require_leases=self.require_leases)
        self._persisted_ids: set[str] = set()
        self._persisted_hashes: set[str] = set()
        self._conn = _PostgresConnection(database_url)
        self._init_schema()
        self._load_from_db()

    def _init_schema(self):
        statements = [
            """CREATE TABLE IF NOT EXISTS objects (
                hash TEXT PRIMARY KEY, content TEXT NOT NULL)""",
            """CREATE TABLE IF NOT EXISTS events (
                seq BIGSERIAL UNIQUE, event_id TEXT PRIMARY KEY, timestamp TEXT NOT NULL,
                agent_id TEXT NOT NULL, action TEXT NOT NULL,
                payload_json TEXT NOT NULL, metadata_json TEXT)""",
            """CREATE TABLE IF NOT EXISTS leases (
                resource_key TEXT PRIMARY KEY, agent_id TEXT NOT NULL,
                expires_at DOUBLE PRECISION NOT NULL, acquired_at DOUBLE PRECISION NOT NULL,
                fencing_token BIGINT NOT NULL DEFAULT 0)""",
            """CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY, value TEXT NOT NULL)""",
            """CREATE TABLE IF NOT EXISTS lease_counters (
                resource_key TEXT PRIMARY KEY, fencing_token BIGINT NOT NULL)""",
            "CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_events_agent ON events(agent_id)",
            "CREATE INDEX IF NOT EXISTS idx_events_action ON events(action)",
        ]
        with self._lock:
            for statement in statements:
                self._conn.execute(statement)
            # Upgrade databases created by the first PostgreSQL schema revision.
            self._conn.execute(
                "ALTER TABLE leases ADD COLUMN IF NOT EXISTS fencing_token BIGINT NOT NULL DEFAULT 0"
            )
            self._conn.commit()

    def _save_lease(self, lease: Lease):
        self._conn.execute(
            """INSERT INTO leases
               (resource_key, agent_id, expires_at, acquired_at, fencing_token)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(resource_key) DO UPDATE SET
                 agent_id=EXCLUDED.agent_id, expires_at=EXCLUDED.expires_at,
                 acquired_at=EXCLUDED.acquired_at, fencing_token=EXCLUDED.fencing_token""",
            (lease.resource_key, lease.agent_id, lease.expires_at,
             lease.acquired_at, lease.fencing_token),
        )
        self._conn.execute(
            """INSERT INTO lease_counters (resource_key, fencing_token) VALUES (?, ?)
               ON CONFLICT(resource_key) DO UPDATE
               SET fencing_token = GREATEST(lease_counters.fencing_token, EXCLUDED.fencing_token)""",
            (lease.resource_key, lease.fencing_token),
        )
