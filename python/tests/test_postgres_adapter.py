from cerbere_cohort.postgres import _Connection, _row_factory


def test_begin_immediate_becomes_transaction():
    assert _Connection._translate("BEGIN IMMEDIATE") == "BEGIN"


def test_sqlite_placeholders_and_rowid_are_translated():
    sql = "SELECT * FROM events WHERE agent_id = ? ORDER BY rowid"
    assert _Connection._translate(sql) == "SELECT * FROM cohort_events WHERE agent_id = %s ORDER BY seq"


def test_insert_or_ignore_is_translated_to_postgres_upsert():
    sql = "INSERT OR IGNORE INTO objects (hash, content) VALUES (?, ?)"
    translated = _Connection._translate(sql)
    assert translated.startswith("INSERT INTO cohort_objects")
    assert "ON CONFLICT DO NOTHING" in translated
    assert "%s" in translated


def test_insert_or_replace_is_translated_to_postgres_upsert():
    sql = "INSERT OR REPLACE INTO leases (resource_key, agent_id, expires_at, acquired_at, fencing_token) VALUES (?, ?, ?, ?, ?)"
    translated = _Connection._translate(sql)
    assert "ON CONFLICT (resource_key) DO UPDATE SET" in translated
    assert "agent_id=EXCLUDED.agent_id" in translated


def test_row_factory_handles_commands_without_result_columns():
    class CommandCursor:
        description = None

    make_row = _row_factory(CommandCursor())
    assert make_row(()) == ()



def test_postgres_tables_are_namespaced_to_avoid_shared_database_collisions():
    sql = _Connection._translate(
        "CREATE INDEX IF NOT EXISTS idx_events_action ON events(action)"
    )
    assert "cohort_idx_events_action" in sql
    assert "ON cohort_events(action)" in sql


def test_api_branch_table_is_namespaced():
    sql = _Connection._translate(
        "SELECT * FROM api_branches WHERE branch_id = ?"
    )
    assert sql == "SELECT * FROM cohort_api_branches WHERE branch_id = %s"
