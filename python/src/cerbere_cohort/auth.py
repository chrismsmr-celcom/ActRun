"""Supabase JWT authentication and single-organization authorization.

Production is deliberately single-tenant until every runtime table and MCP
operation has organization-scoped storage. This fail-closed boundary prevents
one customer's token from reading another customer's shared workspace.
"""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Any
from uuid import UUID

import jwt
from fastapi import Depends, Header, HTTPException


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} must be configured when production authentication is enabled")
    return value


@lru_cache(maxsize=1)
def _jwks_client():
    from jwt import PyJWKClient
    supabase_url = _required_env("SUPABASE_URL").rstrip("/")
    return PyJWKClient(
        f"{supabase_url}/auth/v1/.well-known/jwks.json",
        cache_jwk_set=True,
        lifespan=300,
        timeout=5,
    )


def _decode_access_token(token: str) -> dict[str, Any]:
    try:
        signing_key = _jwks_client().get_signing_key_from_jwt(token)
        issuer = _required_env("SUPABASE_URL").rstrip("/") + "/auth/v1"
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256", "RS256"],
            audience="authenticated",
            issuer=issuer,
            options={"require": ["exp", "iat", "sub", "iss", "aud"]},
            leeway=30,
        )
        UUID(str(claims["sub"]))
        return claims
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired Supabase access token") from exc


def require_workspace_member(
    authorization: str | None = Header(default=None),
    x_organization_id: str | None = Header(default=None, alias="X-Organization-ID"),
) -> dict[str, Any]:
    """Authenticate user and authorize membership in the configured tenant."""
    # Local SQLite mode remains convenient for development and unit tests.
    if not os.getenv("DATABASE_URL", "").strip():
        return {"user_id": "local", "organization_id": "local", "role": "owner"}

    configured_org = _required_env("COHORT_ORGANIZATION_ID")
    try:
        configured_org = str(UUID(configured_org))
    except ValueError as exc:
        raise RuntimeError("COHORT_ORGANIZATION_ID must be a UUID") from exc

    if not x_organization_id:
        raise HTTPException(status_code=400, detail="X-Organization-ID header is required")
    try:
        requested_org = str(UUID(x_organization_id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="X-Organization-ID must be a UUID") from exc

    # Fail closed: current runtime state is global, so this release only allows
    # one explicitly configured organization. Additional tenants are rejected.
    if requested_org != configured_org:
        raise HTTPException(status_code=403, detail="This Cohort deployment is not enabled for that organization")

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Bearer access token required")
    claims = _decode_access_token(authorization[7:].strip())
    user_id = str(UUID(str(claims["sub"])))

    try:
        import psycopg
        with psycopg.connect(_required_env("DATABASE_URL"), connect_timeout=5) as conn:
            row = conn.execute(
                """SELECT role FROM public.cohort_memberships
                   WHERE organization_id = %s AND user_id = %s AND status = 'active'""",
                (requested_org, user_id),
            ).fetchone()
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Unable to verify organization membership") from exc

    if not row:
        raise HTTPException(status_code=403, detail="User is not an active member of this organization")

    return {
        "user_id": user_id,
        "organization_id": requested_org,
        "role": row[0],
        "email": claims.get("email"),
    }


def require_workspace_writer(context: dict[str, Any] = Depends(require_workspace_member)) -> dict[str, Any]:
    """Require an active member with write privileges."""
    if context is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    if context.get("role") not in {"owner", "admin", "member"} and context.get("user_id") != "local":
        raise HTTPException(status_code=403, detail="Workspace write permission required")
    return context
