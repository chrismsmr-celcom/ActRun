from threading import RLock

from cerbere_cohort.postgres import PostgresPersistentWorkspace


class SchemaConnection:
    def __init__(self):
        self.statements = []
        self.committed = False

    def execute(self, statement, params=()):
        self.statements.append(statement)

    def commit(self):
        self.committed = True


def test_postgres_schema_upgrades_existing_leases_with_fencing_token():
    workspace = PostgresPersistentWorkspace.__new__(PostgresPersistentWorkspace)
    workspace._lock = RLock()
    workspace._conn = SchemaConnection()

    workspace._init_schema()

    lease_table = next(
        i for i, sql in enumerate(workspace._conn.statements)
        if "CREATE TABLE IF NOT EXISTS leases" in sql
    )
    migration = next(
        i for i, sql in enumerate(workspace._conn.statements)
        if "ALTER TABLE leases ADD COLUMN IF NOT EXISTS fencing_token" in sql
    )
    assert migration > lease_table
    assert "BIGINT NOT NULL DEFAULT 0" in workspace._conn.statements[migration]
    assert workspace._conn.committed
