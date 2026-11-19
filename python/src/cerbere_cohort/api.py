"""Small single-process HTTP adapter for the Cohort Python runtime.

This adapter exposes the existing Workspace/PersistentWorkspace primitives.
It is intentionally documented as single-process: branch handles and the
branch registry are process-local until the runtime grows durable branch IDs.
"""
from __future__ import annotations

import os
import threading
import uuid
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from cerbere_cohort import (
    ConflictError,
    LeaseError,
    PreferBranch,
    PreferHead,
    PreferAgent,
    Resolution,
)
from cerbere_cohort.persistence import PersistentWorkspace

DB_PATH = Path(os.getenv("COHORT_DB_PATH", "./data/cohort.db"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
workspace = PersistentWorkspace(
    DB_PATH,
    require_leases=os.getenv("COHORT_REQUIRE_LEASES", "false").lower() == "true",
)
_lock = threading.RLock()
_branches: dict[str, dict[str, Any]] = {}

app = FastAPI(title="Cerbere Cohort API", version="0.1.0")
origins = [x.strip() for x in os.getenv("COHORT_CORS_ORIGINS", "*").split(",") if x.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class BranchCreate(BaseModel):
    agent_id: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=120)


class BranchWrite(BaseModel):
    key: str = Field(min_length=1, max_length=500)
    value: Any
    intent: str | None = None


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
        "persistence": "sqlite",
        "branch_registry": "process-memory",
    }


@app.get("/api/overview")
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


@app.get("/api/branches")
def list_branches():
    with _lock:
        return {"items": [_branch_summary(k, v) for k, v in _branches.items()]}


@app.post("/api/branches", status_code=201)
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
            "created_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        }
    return _branch_summary(branch_id, _branches[branch_id])


@app.put("/api/branches/{branch_id}/state")
def write_branch(branch_id: str, body: BranchWrite):
    with _lock:
        item = _branches.get(branch_id)
        if not item or item["status"] != "open":
            raise HTTPException(404, "Open branch not found")
        try:
            item["branch"].set(body.key, body.value, intent=body.intent)
        except (LeaseError, ValueError) as exc:
            raise HTTPException(409, detail={"message": str(exc), "code": getattr(exc, "code", "write_error")}) from exc
    return {"ok": True, "branch_id": branch_id, "key": body.key}


@app.post("/api/branches/{branch_id}/commit")
def commit_branch(branch_id: str):
    with _lock:
        item = _branches.get(branch_id)
        if not item or item["status"] != "open":
            raise HTTPException(404, "Open branch not found")
        try:
            snapshot = workspace.commit(item["agent_id"], item["branch"])
            item["status"] = "merged"
            item["conflicting_keys"] = []
            return {"ok": True, "head": snapshot.version_id, "branch": _branch_summary(branch_id, item)}
        except ConflictError as exc:
            item["conflicting_keys"] = list(exc.conflicting_keys)
            return {
                "ok": False,
                "conflict": True,
                "branch": _branch_summary(branch_id, item),
                "conflicting_keys": list(exc.conflicting_keys),
                "head_version": exc.details.get("head_version"),
                "base_version": exc.details.get("base_version"),
            }


@app.get("/api/branches/{branch_id}/conflict")
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


@app.post("/api/branches/{branch_id}/resolve")
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
            return {"ok": True, "head": snapshot.version_id, "branch": _branch_summary(branch_id, item)}
        except ConflictError as exc:
            item["conflicting_keys"] = list(exc.conflicting_keys)
            raise HTTPException(409, detail={"message": str(exc), "conflicting_keys": list(exc.conflicting_keys)}) from exc


@app.get("/api/state")
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


@app.get("/api/events")
def get_events(limit: int = 100):
    if limit < 1 or limit > 1000:
        raise HTTPException(422, "limit must be between 1 and 1000")
    events = workspace.get_events()
    return {"items": [_event_dict(e) for e in events[-limit:]][::-1]}


@app.get("/api/leases")
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


@app.post("/api/leases", status_code=201)
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


@app.delete("/api/leases/{key:path}")
def release_lease(key: str, agent_id: str):
    try:
        workspace.release_lease(agent_id, key)
    except LeaseError as exc:
        raise HTTPException(409, detail={"message": str(exc), "code": exc.code}) from exc
    return {"ok": True}


@app.get("/api/settings")
def get_settings():
    return {
        "require_leases": workspace._workspace._require_leases,
        "persistence": "sqlite",
        "database_path": str(DB_PATH),
        "multi_process": False,
        "authentication": False,
    }


def main():
    """Run the local Cohort HTTP API."""
    import uvicorn
    uvicorn.run(
        "cerbere_cohort.api:app",
        host=os.getenv("COHORT_API_HOST", "127.0.0.1"),
        port=int(os.getenv("COHORT_API_PORT", "8000")),
        reload=False,
    )
