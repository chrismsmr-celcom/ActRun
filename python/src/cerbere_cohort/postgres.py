"""PostgreSQL adapter for Cohort's replay-verified persistence engine."""
from __future__ import annotations

import re
import threading

from .persistence import PersistentWorkspace


class _Row(dict):
    """Dict row that also supports sqlite-style positional indexing."""
    def __getitem__(self, key):
        if isinstance(key, int):
            return tuple(self.values())[key]
        return super().__getitem__(key)


def _row_factory(cursor):
    # PostgreSQL commands such as CREATE TABLE and INSERT may return no
    # result columns. Psycopg still asks for a row factory while processing
    # the command, so provide a harmless tuple factory in that case.
    if cursor.description is None:
        return lambda values: tuple(values)
    names = [column.name for column in cursor.description]
    def make_row(values):
        return _Row(zip(names, values))
    return make_row


class _Connection:
    """Translate the small SQLite SQL subset used by PersistentWorkspace."""
    def __init__(self, dsn: str):
        try:
            import psycopg
        except ImportError as exc:
            raise RuntimeError("Install psycopg[binary]>=3.2 for PostgreSQL support") from exc
        self._db = psycopg.connect(dsn, row_factory=_row_factory, connect_timeout=15, autocommit=True)
        self._lock = threading.RLock()

    @staticmethod
    def _translate(sql: str) -> str:
        statement = sql.strip()
        upper = statement.upper()
        if upper == "BEGIN IMMEDIATE":
            return "BEGIN"
        ignore_insert = bool(re.match(r"^INSERT\s+OR\s+IGNORE\s+INTO", statement, flags=re.I))
        statement = re.sub(r"^INSERT\s+OR\s+IGNORE\s+INTO", "INSERT INTO", statement, flags=re.I)
        if re.match(r"^INSERT\s+OR\s+REPLACE\s+INTO", statement, flags=re.I):
            statement = re.sub(r"^INSERT\s+OR\s+REPLACE\s+INTO", "INSERT INTO", statement, flags=re.I)
            match = re.search(r"INSERT INTO\s+([\w]+)\s*\(([^)]+)\)\s*VALUES", statement, flags=re.I)
            if not match:
                raise ValueError("Unsupported INSERT OR REPLACE statement")
            table = match.group(1)
            columns = [c.strip() for c in match.group(2).split(",")]
            key = "resource_key" if table.lower() == "leases" else columns[0]
            updates = [c for c in columns if c != key]
            clause = ", ".join(f"{c}=EXCLUDED.{c}" for c in updates)
            statement += f" ON CONFLICT ({key}) DO UPDATE SET {clause}"
        # Keep Cohort's tables isolated from generic tables that may already
        # exist in a shared Supabase/Postgres database (notably public.events).
        # Apply this mapping to reads, writes, indexes, and branch storage.
        namespaced = {
            "objects": "cohort_objects",
            "events": "cohort_events",
            "leases": "cohort_leases",
            "metadata": "cohort_metadata",
            "lease_counters": "cohort_lease_counters",
            "api_branches": "cohort_api_branches",
            "idx_events_timestamp": "cohort_idx_events_timestamp",
            "idx_events_agent": "cohort_idx_events_agent",
            "idx_events_action": "cohort_idx_events_action",
        }
        for source, target in namespaced.items():
            statement = re.sub(rf"\\b{source}\\b", target, statement, flags=re.I)
        statement = re.sub(r"ORDER\\s+BY\\s+rowid", "ORDER BY seq", statement, flags=re.I)
        statement = statement.replace("MAX(fencing_token, excluded.fencing_token)",
                                      "GREATEST(cohort_lease_counters.fencing_token, EXCLUDED.fencing_token)")
        if ignore_insert and "ON CONFLICT" not in statement.upper():
            statement += " ON CONFLICT DO NOTHING"
        return statement.replace("?", "%s")

    def execute(self, sql: str, params=()):
        with self._lock:
            cursor = self._db.execute(self._translate(sql), params)
            if sql.strip().upper() == "BEGIN IMMEDIATE":
                self._db.execute("SELECT pg_advisory_xact_lock(hashtext('cerbere-cohort-runtime'))")
            return cursor

    def commit(self):
        with self._lock:
            self._db.commit()

    def rollback(self):
        with self._lock:
            self._db.rollback()

    def close(self):
        self._db.close()


class PostgresPersistentWorkspace(PersistentWorkspace):
    """PersistentWorkspace backed by Supabase PostgreSQL.

    DATABASE_URL is read from the deployment environment by the caller.
    The advisory transaction lock serializes workspace writes across instances.
    """
    def __init__(self, database_url: str, auto_save: bool = True,
                 require_leases: bool = False):
        if not database_url.startswith(("postgres://", "postgresql://")):
            raise ValueError("A PostgreSQL DATABASE_URL is required")
        self.db_path = database_url
        self.auto_save = auto_save
        self.require_leases = require_leases
        self._lock = threading.RLock()
        from .workspace import Workspace
        self._workspace = Workspace(require_leases=require_leases)
        self._persisted_ids: set[str] = set()
        self._persisted_hashes: set[str] = set()
        self._conn = _Connection(database_url)
        self._init_schema()
        self._load_from_db()

    def _init_schema(self):
        schema = (
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
        )
        with self._lock:
            for statement in schema:
                self._conn.execute(statement)
            self._conn.commit()
