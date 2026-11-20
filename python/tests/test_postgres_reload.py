from threading import RLock

from cerbere_cohort.postgres import PostgresPersistentWorkspace
from cerbere_cohort.workspace import Workspace


class FakeConnection:
    def __init__(self):
        self.queries = []

    def execute(self, sql, params=()):
        self.queries.append(sql)
        if "FROM objects" in sql:
            return []
        if "FROM events" in sql:
            return []
        if "FROM lease_counters" in sql:
            return [{"resource_key": "docs/1", "fencing_token": 7}]
        if "FROM leases" in sql:
            return [{
                "resource_key": "docs/1",
                "agent_id": "worker-b",
                "expires_at": 9999999999.0,
                "acquired_at": 100.0,
                "fencing_token": 7,
            }]
        raise AssertionError(f"Unexpected SQL: {sql}")


def test_postgres_reload_uses_postgres_compatible_queries_and_restores_leases():
    workspace = PostgresPersistentWorkspace.__new__(PostgresPersistentWorkspace)
    workspace._lock = RLock()
    workspace.require_leases = True
    workspace._persisted_ids = set()
    workspace._persisted_hashes = set()
    workspace._workspace = Workspace(require_leases=True)
    workspace._conn = FakeConnection()

    workspace._load_from_db()

    assert all("PRAGMA" not in query.upper() for query in workspace._conn.queries)
    event_query = next(q for q in workspace._conn.queries if "FROM events" in q)
    assert "ORDER BY seq" in event_query
    assert workspace._workspace._lease_manager._fencing_counters["docs/1"] == 7
    lease = workspace._workspace._lease_manager.get_active_leases()["docs/1"]
    assert lease.agent_id == "worker-b"
    assert lease.fencing_token == 7
