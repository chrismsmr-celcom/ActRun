"""Beta hardening: membership cache, Postgres reconnect, fail-closed startup, payload bounds."""
import os
import subprocess
import sys
import types

import pytest

from cerbere_cohort import auth
from cerbere_cohort.postgres import _Connection

ORG = "11111111-1111-4111-8111-111111111111"
USER = "22222222-2222-4222-8222-222222222222"


def _fake_psycopg(counter):
    class Result:
        def fetchone(self):
            return ("member",)

    class Conn:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def execute(self, *args, **kwargs):
            return Result()

    def connect(*args, **kwargs):
        counter["n"] += 1
        return Conn()

    return types.SimpleNamespace(connect=connect)


def test_membership_lookup_is_cached(monkeypatch):
    counter = {"n": 0}
    monkeypatch.setitem(sys.modules, "psycopg", _fake_psycopg(counter))
    monkeypatch.setenv("DATABASE_URL", "postgresql://example")
    monkeypatch.setenv("COHORT_ORGANIZATION_ID", ORG)
    monkeypatch.setattr(auth, "_decode_access_token", lambda token: {"sub": USER, "email": "a@b.co"})
    auth._membership_cache.clear()
    for _ in range(3):
        ctx = auth.require_workspace_member(authorization="Bearer t", x_organization_id=ORG)
    assert ctx["role"] == "member" and ctx["user_id"] == USER
    assert counter["n"] == 1, "membership must be looked up once within the TTL"
    auth._membership_cache.clear()


def test_membership_cache_expires(monkeypatch):
    counter = {"n": 0}
    monkeypatch.setitem(sys.modules, "psycopg", _fake_psycopg(counter))
    monkeypatch.setenv("DATABASE_URL", "postgresql://example")
    monkeypatch.setenv("COHORT_ORGANIZATION_ID", ORG)
    monkeypatch.setattr(auth, "_decode_access_token", lambda token: {"sub": USER})
    auth._membership_cache.clear()
    auth.require_workspace_member(authorization="Bearer t", x_organization_id=ORG)
    key = (ORG, USER)
    auth._membership_cache[key] = (0.0, "member")  # already expired
    auth.require_workspace_member(authorization="Bearer t", x_organization_id=ORG)
    assert counter["n"] == 2
    auth._membership_cache.clear()


class _FakeDb:
    def __init__(self, fail_times, errors):
        self.fail_times, self.errors, self.closed, self.broken, self.calls = fail_times, errors, False, False, 0

    def execute(self, sql, params=()):
        self.calls += 1
        if self.fail_times > 0:
            self.fail_times -= 1
            raise self.errors.OperationalError("server closed the connection unexpectedly")
        return "cursor"

    def close(self):
        self.closed = True

    def commit(self):
        pass

    def rollback(self):
        pass


def _connection(fail_times):
    errors = types.SimpleNamespace(OperationalError=type("OperationalError", (Exception,), {}),
                                   InterfaceError=type("InterfaceError", (Exception,), {}))
    conn = object.__new__(_Connection)
    import threading
    conn._psycopg, conn._lock, conn._in_txn = errors, threading.RLock(), False
    conn._db = _FakeDb(fail_times, errors)
    conn._connect = lambda: _FakeDb(0, errors)
    return conn, errors


def test_postgres_reconnects_after_dropped_connection():
    conn, _ = _connection(fail_times=1)
    first = conn._db
    assert conn.execute("SELECT 1") == "cursor"
    assert first.closed and conn._db is not first


def test_postgres_does_not_replay_inside_transaction():
    conn, errors = _connection(fail_times=1)
    conn._in_txn = True
    with pytest.raises(errors.OperationalError):
        conn.execute("INSERT INTO events VALUES (?)", ("x",))
    conn.rollback()
    assert conn._in_txn is False


def test_hosted_deployment_refuses_to_start_without_database():
    env = {k: v for k, v in os.environ.items() if k not in {"DATABASE_URL", "COHORT_DB_PATH"}}
    env.update({"RENDER": "true", "COHORT_ENV": "production"})
    proc = subprocess.run([sys.executable, "-c", "import cerbere_cohort.api"], env=env,
                          capture_output=True, text=True)
    assert proc.returncode != 0
    assert "DATABASE_URL is required" in proc.stderr


def test_branch_value_is_bounded():
    from cerbere_cohort.api import BranchWrite, MAX_VALUE_BYTES
    from pydantic import ValidationError
    assert BranchWrite(key="k", value={"ok": True}).value == {"ok": True}
    with pytest.raises(ValidationError):
        BranchWrite(key="k", value="x" * (MAX_VALUE_BYTES + 1))
