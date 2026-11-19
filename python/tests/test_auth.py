from fastapi import HTTPException

from cerbere_cohort.auth import require_workspace_member, require_workspace_writer


def test_local_development_bypasses_supabase(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    context = require_workspace_member()
    assert context["user_id"] == "local"
    assert context["role"] == "owner"


def test_production_requires_organization_header(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://example")
    monkeypatch.setenv("COHORT_ORGANIZATION_ID", "11111111-1111-4111-8111-111111111111")
    try:
        require_workspace_member()
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
