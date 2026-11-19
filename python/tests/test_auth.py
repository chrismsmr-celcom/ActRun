from fastapi import HTTPException

from cerbere_cohort.auth import require_workspace_member, require_workspace_writer


def test_local_development_bypasses_supabase(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    context = require_workspace_member(authorization=None, x_organization_id=None)
    assert context["user_id"] == "local"
    assert context["role"] == "owner"


def test_production_requires_organization_header(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://example")
    monkeypatch.setenv("COHORT_ORGANIZATION_ID", "11111111-1111-4111-8111-111111111111")
    try:
        require_workspace_member(authorization=None, x_organization_id=None)
    except HTTPException as exc:
        assert exc.status_code == 400
        assert "X-Organization-ID" in exc.detail
    else:
        raise AssertionError("Missing organization header must be rejected")


def test_production_rejects_other_organization(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://example")
    monkeypatch.setenv("COHORT_ORGANIZATION_ID", "11111111-1111-4111-8111-111111111111")
    try:
        require_workspace_member(
            authorization="Bearer not-used",
            x_organization_id="22222222-2222-4222-8222-222222222222",
        )
    except HTTPException as exc:
        assert exc.status_code == 403
    else:
        raise AssertionError("A different organization must be rejected")


def test_viewer_cannot_write():
    try:
        require_workspace_writer({"user_id": "u", "role": "viewer"})
    except HTTPException as exc:
        assert exc.status_code == 403
    else:
        raise AssertionError("Viewer role must be read-only")


def test_member_can_write():
    context = {"user_id": "u", "role": "member"}
    assert require_workspace_writer(context) == context


class _FakeMembershipDB:
    def __init__(self, role="owner", error=None):
        self.role = role
        self.error = error
        self.calls = []

    def execute(self, sql, params):
        self.calls.append((sql, params))
        if self.error:
            raise self.error
        return _FakeCursor((self.role,))


class _FakeCursor:
    def __init__(self, row):
        self.row = row

    def fetchone(self):
        return self.row


def test_production_membership_uses_configured_runtime_connection(monkeypatch):
    import cerbere_cohort.auth as auth

    monkeypatch.setenv("DATABASE_URL", "postgresql://example")
    monkeypatch.setenv("COHORT_ORGANIZATION_ID", "11111111-1111-4111-8111-111111111111")
    monkeypatch.setattr(auth, "_decode_access_token", lambda token: {
        "sub": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa", "email": "owner@example.com"
    })
    monkeypatch.setattr(auth, "_membership_cache", {})
    db = _FakeMembershipDB(role="owner")
    auth.configure_membership_db(db)

    result = require_workspace_member(
        authorization="Bearer valid-token",
        x_organization_id="11111111-1111-4111-8111-111111111111",
    )

    assert result["role"] == "owner"
    assert len(db.calls) == 1
    assert "public.cohort_memberships" in db.calls[0][0]
    assert db.calls[0][1] == (
        "11111111-1111-4111-8111-111111111111",
        "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
    )


def test_production_membership_db_failure_is_fail_closed(monkeypatch):
    import cerbere_cohort.auth as auth

    monkeypatch.setenv("DATABASE_URL", "postgresql://example")
    monkeypatch.setenv("COHORT_ORGANIZATION_ID", "11111111-1111-4111-8111-111111111111")
    monkeypatch.setattr(auth, "_decode_access_token", lambda token: {
        "sub": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    })
    monkeypatch.setattr(auth, "_membership_cache", {})
    auth.configure_membership_db(_FakeMembershipDB(error=RuntimeError("database unavailable")))

    try:
        require_workspace_member(
            authorization="Bearer valid-token",
            x_organization_id="11111111-1111-4111-8111-111111111111",
        )
    except HTTPException as exc:
        assert exc.status_code == 503
        assert exc.detail == "Unable to verify organization membership"
    else:
        raise AssertionError("Database failures must fail closed")
