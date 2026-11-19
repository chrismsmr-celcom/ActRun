"""HTTP adapter for the Cohort runtime.

Workspace state and branch working copies are persisted in the configured
database. Until organization-scoped access and cross-instance branch locking
are implemented, deploy this API as a single instance.
"""
from __future__ import annotations

import datetime
import json
import os
import threading
import uuid
from pathlib import Path
from typing import Any, Literal

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from cerbere_cohort.workspace import Branch
from cerbere_cohort.auth import require_workspace_member, require_workspace_writer

from cerbere_cohort import (
    ConflictError,
    LeaseError,
    PreferBranch,
    PreferHead,
    PreferAgent,
    Resolution,
)
from cerbere_cohort.persistence import PersistentWorkspace
from cerbere_cohort.postgres import PostgresPersistentWorkspace

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
DB_PATH = Path(os.getenv("COHORT_DB_PATH", "./data/cohort.db"))
if DATABASE_URL and not DATABASE_URL.startswith(("postgres://", "postgresql://")):
    raise RuntimeError("DATABASE_URL must be a PostgreSQL connection URL")
if DATABASE_URL and (not os.getenv("SUPABASE_URL") or not os.getenv("COHORT_ORGANIZATION_ID")):
    raise RuntimeError("SUPABASE_URL and COHORT_ORGANIZATION_ID are required in production")
# Fail closed: without DATABASE_URL the API runs in the unauthenticated local
# development mode. Never let a hosted deployment fall into it by accident.
_HOSTED = bool(os.getenv("RENDER") or os.getenv("COHORT_ENV", "").lower() == "production")
if _HOSTED and not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is required on hosted deployments; refusing to start without authentication")
if not DATABASE_URL:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
workspace = (
    PostgresPersistentWorkspace(DATABASE_URL)
    if DATABASE_URL.startswith(("postgres://", "postgresql://"))
    else PersistentWorkspace(DB_PATH)
)
workspace._workspace._require_leases = (
    os.getenv("COHORT_REQUIRE_LEASES", "false").lower() == "true"
)
_lock = threading.RLock()
_branches: dict[str, dict[str, Any]] = {}

workspace._conn.execute("CREATE TABLE IF NOT EXISTS api_branches (branch_id TEXT PRIMARY KEY, agent_id TEXT NOT NULL, branch_name TEXT NOT NULL, base_version TEXT NOT NULL, current_data_json TEXT NOT NULL, intents_json TEXT NOT NULL, status TEXT NOT NULL, conflicting_keys_json TEXT NOT NULL, created_at TEXT NOT NULL)")
workspace._conn.commit()

def _save_api_branch(branch_id: str, item: dict[str, Any]) -> None:
    b = item['branch']
    workspace._conn.execute("INSERT INTO api_branches (branch_id, agent_id, branch_name, base_version, current_data_json, intents_json, status, conflicting_keys_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(branch_id) DO UPDATE SET current_data_json=excluded.current_data_json, intents_json=excluded.intents_json, status=excluded.status, conflicting_keys_json=excluded.conflicting_keys_json", (branch_id, item['agent_id'], b.name, b.base_version, json.dumps(b.current_data, ensure_ascii=False), json.dumps(b.intents, ensure_ascii=False), item['status'], json.dumps(item.get('conflicting_keys', [])), item['created_at']))
    workspace._conn.commit()

def _restore_api_branches() -> None:
    committed = {
        (event.agent_id, event.payload.get('branch_name'))
        for event in workspace.get_events()
        if event.action == 'workspace.commit'
    }
    for row in workspace._conn.execute('SELECT * FROM api_branches').fetchall():
        if (row['agent_id'], row['branch_name']) in committed:
            workspace._conn.execute("UPDATE api_branches SET status = 'merged', conflicting_keys_json = '[]' WHERE branch_id = ?", (row['branch_id'],))
            continue
        base = workspace._workspace._snapshots.get(row['base_version'])
        if base is None:
            continue
        b = Branch(row['branch_name'], base, workspace._workspace._lease_manager, row['agent_id'], workspace._workspace._require_leases)
        b.current_data = json.loads(row['current_data_json'])
        b.intents = json.loads(row['intents_json'])
        _branches[row['branch_id']] = {'branch': b, 'agent_id': row['agent_id'], 'status': row['status'], 'conflicting_keys': json.loads(row['conflicting_keys_json']), 'created_at': row['created_at']}
    workspace._conn.commit()

_restore_api_branches()

app = FastAPI(title="Cerbere Cohort API", version="0.1.0")
origins = [x.strip() for x in os.getenv("COHORT_CORS_ORIGINS", "*").split(",") if x.strip()]
if DATABASE_URL and (not os.getenv("COHORT_CORS_ORIGINS") or "*" in origins):
    raise RuntimeError("Set COHORT_CORS_ORIGINS to explicit frontend origins in production")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


MAX_VALUE_BYTES = 256 * 1024


class BranchCreate(BaseModel):
    agent_id: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=120)


class BranchWrite(BaseModel):
    key: str = Field(min_length=1, max_length=500)
    value: Any
    intent: str | None = Field(default=None, max_length=2000)

    @field_validator("value")
    @classmethod
    def _bounded_value(cls, value: Any) -> Any:
        if len(json.dumps(value, ensure_ascii=False, default=str)) > MAX_VALUE_BYTES:
            raise ValueError(f"value exceeds {MAX_VALUE_BYTES} bytes")
        return value


class LeaseRequest(BaseModel):
    agent_id: str = Field(min_length=1, max_length=120)
    key: str = Field(min_length=1, max_length=500)
    duration_seconds: float = Field(default=60, gt=0, le=86400)


class ResolveRequest(BaseModel):
    strategy: Literal["PreferHead", "PreferBranch", "PreferAgent"] = "PreferHead"
    rationale: str = Field(min_length=1, max_length=2000)
    priority: list[str] = Field(default_factory=list)


def _event_dict(event):
    return event.model_dump(mode="json")


def _branch_summary(branch_id: str, item: dict[str, Any]) -> dict[str, Any]:
    branch = item["branch"]
    return {
        "id": branch_id,
        "name": branch.name,
        "agent_id": item["agent_id"],
        "base_version": branch.base_version,
        "status": item["status"],
        "conflicting_keys": item.get("conflicting_keys", []),
        "created_at": item["created_at"],
    }


@app.get("/api/health")
def health():
    return {
        "ok": True,
        "service": "cerbere-cohort",
        "runtime": "python",
        "persistence": "postgresql" if DATABASE_URL.startswith(("postgres://", "postgresql://")) else "sqlite",
        "branch_registry": "database",
        "authentication": "supabase" if DATABASE_URL else "development-bypass",
    }


@app.get("/api/overview", dependencies=[Depends(require_workspace_member)])
def overview():
    events = workspace.get_events()
    leases = workspace._workspace._lease_manager.get_active_leases()
    successful = sum(e.action == "workspace.commit" for e in events)
    conflicts = sum(e.action == "coordination.conflict" for e in events)
    return {
        "head": workspace.head.version_id,
        "key_count": len(workspace.head.entries),
        "snapshot_count": workspace.get_snapshot_count(),
        "event_count": workspace.get_event_count(),
        "active_lease_count": len(leases),
        "commit_count": successful,
        "conflict_count": conflicts,
        "branches": len(_branches),
        "sample_data": False,
    }


@app.get("/api/branches", dependencies=[Depends(require_workspace_member)])
def list_branches():
    with _lock:
        return {"items": [_branch_summary(k, v) for k, v in _branches.items()]}


@app.get("/api/branches/{branch_id}/diff", dependencies=[Depends(require_workspace_member)])
def get_branch_diff(branch_id: str):
    """Preview every key changed by a branch against its base and current HEAD."""
    with _lock:
        item = _branches.get(branch_id)
        if not item:
            raise HTTPException(404, "Branch not found")
        branch = item["branch"]
        base = workspace._workspace._snapshots.get(branch.base_version)
        if base is None:
            raise HTTPException(409, "Branch base snapshot is no longer available")

        base_data = base.data
        branch_data = branch.current_data
        head_data = workspace.head.data
        changed_keys = sorted(
            key
            for key in set(base_data) | set(branch_data)
            if (key in base_data) != (key in branch_data)
            or base_data.get(key) != branch_data.get(key)
        )
        changes = []
        for key in changed_keys:
            base_present = key in base_data
            branch_present = key in branch_data
            head_present = key in head_data
            changes.append({
                "key": key,
                "base": base_data.get(key),
                "proposed": branch_data.get(key),
                "head": head_data.get(key),
                "base_present": base_present,
                "proposed_present": branch_present,
                "head_present": head_present,
                "head_changed_since_base": (
                    base_present != head_present
                    or base_data.get(key) != head_data.get(key)
                ),
                "intent": branch.intents.get(key),
            })

        return {
            "branch": _branch_summary(branch_id, item),
            "base_version": base.version_id,
            "head_version": workspace.head.version_id,
            "change_count": len(changes),
            "changes": changes,
        }


@app.post("/api/branches", status_code=201, dependencies=[Depends(require_workspace_writer)])
def create_branch(body: BranchCreate):
    branch_id = str(uuid.uuid4())
    try:
        branch = workspace.create_branch(body.agent_id, body.name)
    except Exception as exc:
        raise HTTPException(400, str(exc)) from exc
    with _lock:
        _branches[branch_id] = {
            "branch": branch,
            "agent_id": body.agent_id,
            "status": "open",
            "conflicting_keys": [],
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        _save_api_branch(branch_id, _branches[branch_id])
    return _branch_summary(branch_id, _branches[branch_id])


@app.put("/api/branches/{branch_id}/state", dependencies=[Depends(require_workspace_writer)])
def write_branch(branch_id: str, body: BranchWrite):
    with _lock:
        item = _branches.get(branch_id)
        if not item or item["status"] != "open":
            raise HTTPException(404, "Open branch not found")
        try:
            item["branch"].set(body.key, body.value, intent=body.intent)
            _save_api_branch(branch_id, item)
        except (LeaseError, ValueError) as exc:
            raise HTTPException(409, detail={"message": str(exc), "code": getattr(exc, "code", "write_error")}) from exc
    return {"ok": True, "branch_id": branch_id, "key": body.key}


@app.post("/api/branches/{branch_id}/commit", dependencies=[Depends(require_workspace_writer)])
def commit_branch(branch_id: str):
    with _lock:
        item = _branches.get(branch_id)
        if not item or item["status"] != "open":
            raise HTTPException(404, "Open branch not found")
        try:
            snapshot = workspace.commit(item["agent_id"], item["branch"])
            item["status"] = "merged"
            item["conflicting_keys"] = []
            _save_api_branch(branch_id, item)
            return {"ok": True, "head": snapshot.version_id, "branch": _branch_summary(branch_id, item)}
        except ConflictError as exc:
            item["conflicting_keys"] = list(exc.conflicting_keys)
            _save_api_branch(branch_id, item)
            return {
                "ok": False,
                "conflict": True,
                "branch": _branch_summary(branch_id, item),
                "conflicting_keys": list(exc.conflicting_keys),
                "head_version": exc.details.get("head_version"),
                "base_version": exc.details.get("base_version"),
            }


@app.get("/api/branches/{branch_id}/conflict", dependencies=[Depends(require_workspace_member)])
def get_branch_conflict(branch_id: str):
    with _lock:
        item = _branches.get(branch_id)
        if not item or item["status"] != "open":
            raise HTTPException(404, "Open branch not found")
        keys = item.get("conflicting_keys", [])
        if not keys:
            raise HTTPException(409, "Branch has no recorded conflict")
        base = workspace._workspace._snapshots.get(item["branch"].base_version)
        if base is None:
            raise HTTPException(409, "Branch base snapshot is no longer available")
        head = workspace.head
        branch_data = item["branch"].current_data
        return {
            "branch_id": branch_id,
            "base_version": base.version_id,
            "head_version": head.version_id,
            "conflicts": [
                {
                    "key": key,
                    "base": base.data.get(key),
                    "head": head.data.get(key),
                    "branch": branch_data.get(key),
                    "base_present": key in base.entries,
                    "head_present": key in head.entries,
                    "branch_present": key in branch_data,
                }
                for key in keys
            ],
        }


@app.post("/api/branches/{branch_id}/resolve", dependencies=[Depends(require_workspace_writer)])
def resolve_branch(branch_id: str, body: ResolveRequest):
    with _lock:
        item = _branches.get(branch_id)
        if not item or item["status"] != "open":
            raise HTTPException(404, "Open branch not found")
        if not item.get("conflicting_keys"):
            raise HTTPException(409, "Branch has no recorded conflict")
        if body.strategy == "PreferHead":
            resolver = PreferHead()
        elif body.strategy == "PreferBranch":
            resolver = PreferBranch()
        else:
            if not body.priority:
                raise HTTPException(422, "priority is required for PreferAgent")
            resolver = PreferAgent(body.priority)
        # Keep the user rationale in the event metadata through a small resolver wrapper.
        class AuditedResolver:
            name = resolver.name
            def resolve(self, conflict):
                decision = resolver.resolve(conflict)
                if decision is None:
                    return None
                return Resolution(
                    present=decision.present,
                    value=decision.value,
                    rationale=body.rationale,
                )
        try:
            snapshot = workspace.commit(item["agent_id"], item["branch"], resolver=AuditedResolver())
            item["status"] = "merged"
            item["conflicting_keys"] = []
            _save_api_branch(branch_id, item)
            return {"ok": True, "head": snapshot.version_id, "branch": _branch_summary(branch_id, item)}
        except ConflictError as exc:
            item["conflicting_keys"] = list(exc.conflicting_keys)
            _save_api_branch(branch_id, item)
            raise HTTPException(409, detail={"message": str(exc), "conflicting_keys": list(exc.conflicting_keys)}) from exc


@app.get("/api/state", dependencies=[Depends(require_workspace_member)])
def get_state():
    head = workspace.head
    return {
        "head": head.version_id,
        "parent": head.parent_version,
        "items": [
            {"key": key, "value_hash": digest, "value": workspace.store.get(digest)}
            for key, digest in head.entries.items()
        ],
    }


@app.get("/api/events", dependencies=[Depends(require_workspace_member)])
def get_events(limit: int = 100):
    if limit < 1 or limit > 1000:
        raise HTTPException(422, "limit must be between 1 and 1000")
    events = workspace.get_events()
    return {"items": [_event_dict(e) for e in events[-limit:]][::-1]}


@app.get("/api/leases", dependencies=[Depends(require_workspace_member)])
def get_leases():
    leases = workspace._workspace._lease_manager.get_active_leases()
    return {
        "items": [
            {
                "key": lease.resource_key,
                "agent_id": lease.agent_id,
                "expires_at": lease.expires_at,
                "acquired_at": lease.acquired_at,
                "fencing_token": lease.fencing_token,
            }
            for lease in leases.values()
        ]
    }


@app.post("/api/leases", status_code=201, dependencies=[Depends(require_workspace_writer)])
def acquire_lease(body: LeaseRequest):
    try:
        lease = workspace.acquire_lease(body.agent_id, body.key, body.duration_seconds)
    except LeaseError as exc:
        raise HTTPException(409, detail={"message": str(exc), "code": exc.code, "details": exc.details}) from exc
    return {
        "key": lease.resource_key,
        "agent_id": lease.agent_id,
        "expires_at": lease.expires_at,
        "acquired_at": lease.acquired_at,
        "fencing_token": lease.fencing_token,
    }


@app.delete("/api/leases/{key:path}", dependencies=[Depends(require_workspace_writer)])
def release_lease(key: str, agent_id: str):
    try:
        workspace.release_lease(agent_id, key)
    except LeaseError as exc:
        raise HTTPException(409, detail={"message": str(exc), "code": exc.code}) from exc
    return {"ok": True}


@app.get("/api/settings", dependencies=[Depends(require_workspace_member)])
def get_settings():
    return {
        "require_leases": workspace._workspace._require_leases,
        "persistence": "postgresql" if DATABASE_URL.startswith(("postgres://", "postgresql://")) else "sqlite",
        "database_path": "managed" if DATABASE_URL.startswith(("postgres://", "postgresql://")) else str(DB_PATH),
        "multi_process": False,
        "database_transactions": DATABASE_URL.startswith(("postgres://", "postgresql://")),
        "authentication": "supabase" if DATABASE_URL else "development-bypass",
    }


def main():
    """Run the local Cohort HTTP API."""
    import uvicorn
    uvicorn.run(
        "cerbere_cohort.api:app",
        host=os.getenv("COHORT_API_HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", os.getenv("COHORT_API_PORT", "8000"))),
        reload=False,
    )
