"""Unit tests for SQLite-to-PostgreSQL SQL compatibility translation."""
from cerbere_cohort.postgres import _Connection


def test_begin_immediate_becomes_transaction_begin():
    assert _Connection._translate("BEGIN IMMEDIATE") == "BEGIN"


def test_insert_or_ignore_uses_postgres_conflict_clause():
    sql = _Connection._translate(
        "INSERT OR IGNORE INTO events (event_id, action) VALUES (?, ?)"
    )
    assert sql == (
        "INSERT INTO public.cohort_events (event_id, action) VALUES (%s, %s) "
        "ON CONFLICT DO NOTHING"
    )


def test_insert_or_replace_becomes_upsert():
    sql = _Connection._translate(
        "INSERT OR REPLACE INTO leases "
        "(resource_key, agent_id, expires_at) VALUES (?, ?, ?)"
    )
    assert "ON CONFLICT (resource_key) DO UPDATE SET" in sql
    assert "agent_id=EXCLUDED.agent_id" in sql
    assert "expires_at=EXCLUDED.expires_at" in sql
    assert "?" not in sql


def test_event_order_uses_persistent_sequence():
    sql = _Connection._translate("SELECT * FROM events ORDER BY rowid")
    assert sql == "SELECT * FROM public.cohort_events ORDER BY seq"


def test_lease_counter_uses_greatest():
    sql = _Connection._translate(
        "INSERT INTO lease_counters (resource_key, fencing_token) VALUES (?, ?) "
        "ON CONFLICT(resource_key) DO UPDATE SET "
        "fencing_token = MAX(fencing_token, excluded.fencing_token)"
    )
    assert "GREATEST(cohort_lease_counters.fencing_token, EXCLUDED.fencing_token)" in sql
