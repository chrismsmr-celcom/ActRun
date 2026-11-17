"""Cerbere Cohort MCP server.

The default transport is Streamable HTTP so multiple MCP clients can share one
SQLite-backed workspace. Bind to loopback unless an authenticated proxy is used.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import threading
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from cerbere_cohort.lease import LeaseError
from cerbere_cohort.merge import ConflictError
from cerbere_cohort.persistence import PersistentWorkspace
from cerbere_cohort.workspace import Branch


class CohortService:
    """Thread-safe MCP-facing facade over PersistentWorkspace."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.workspace = PersistentWorkspace(self.db_path)
        self._db = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS mcp_branches (
                agent_id TEXT NOT NULL,
                branch_name TEXT NOT NULL,
                base_version TEXT NOT NULL,
                current_data_json TEXT NOT NULL,
                intents_json TEXT NOT NULL,
                PRIMARY KEY (agent_id, branch_name)
            )
            """
        )
        self._db.commit()
        self._branches: dict[tuple[str, str], Branch] = {}
        self._restore_branches()

    def _restore_branches(self) -> None:
        """Restore uncommitted branches after a process restart."""
        with self._lock:
            rows = self._db.execute("SELECT * FROM mcp_branches").fetchall()
            for row in rows:
                base = self.workspace._workspace._snapshots.get(row["base_version"])
                if base is None:
                    raise RuntimeError(
                        f"Cannot restore branch {row['agent_id']}:{row['branch_name']}: "
                        "its base snapshot is missing"
                    )
                branch = Branch(
                    name=row["branch_name"],
                    base_snapshot=base,
                    lease_manager=self.workspace._workspace._lease_manager,
                    agent_id=row["agent_id"],
                    require_leases=self.workspace._workspace._require_leases,
                )
                branch.current_data = json.loads(row["current_data_json"])
                branch.intents = json.loads(row["intents_json"])
                self._branches[(row["agent_id"], row["branch_name"])] = branch

    def _persist_branch(self, agent_id: str, branch: Branch) -> None:
        self._db.execute(
            """
            INSERT INTO mcp_branches
                (agent_id, branch_name, base_version, current_data_json, intents_json)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(agent_id, branch_name) DO UPDATE SET
                base_version=excluded.base_version,
                current_data_json=excluded.current_data_json,
                intents_json=excluded.intents_json
            """,
            (
                agent_id,
                branch.name,
                branch.base_version,
                json.dumps(branch.current_data, ensure_ascii=False, sort_keys=True),
                json.dumps(branch.intents, ensure_ascii=False, sort_keys=True),
            ),
        )
        self._db.commit()

    def _branch(self, agent_id: str, branch_name: str) -> Branch:
        try:
            return self._branches[(agent_id, branch_name)]
        except KeyError as exc:
            raise ValueError(
                f"Branch '{branch_name}' not found for agent '{agent_id}'. "
                "Create it first with workspace_create_branch."
            ) from exc

    def get_state(self) -> dict[str, Any]:
        with self._lock:
            return {
                "head_version": self.workspace.head.version_id,
                "state": self.workspace.head.data,
            }

    def create_branch(self, agent_id: str, branch_name: str) -> dict[str, str]:
        self._validate_identity(agent_id, branch_name)
        with self._lock:
            key = (agent_id, branch_name)
            if key in self._branches:
                raise ValueError(f"Branch '{branch_name}' already exists for '{agent_id}'.")
            branch = self.workspace.create_branch(agent_id, branch_name)
            self._branches[key] = branch
            self._persist_branch(agent_id, branch)
            return {
                "agent_id": agent_id,
                "branch_name": branch_name,
                "base_version": branch.base_version,
            }

    def read_branch(self, agent_id: str, branch_name: str, key: str) -> dict[str, Any]:
        with self._lock:
            branch = self._branch(agent_id, branch_name)
            return {"key": key, "exists": key in branch.current_data, "value": branch.get(key)}

    def write_branch(
        self, agent_id: str, branch_name: str, key: str, value: Any, intent: str | None = None
    ) -> dict[str, Any]:
        with self._lock:
            branch = self._branch(agent_id, branch_name)
            branch.set(key, value, intent=intent)
            self._persist_branch(agent_id, branch)
            return {"updated": True, "key": key, "branch_name": branch_name}

    def delete_branch_key(
        self, agent_id: str, branch_name: str, key: str, intent: str | None = None
    ) -> dict[str, Any]:
        with self._lock:
            branch = self._branch(agent_id, branch_name)
            branch.delete(key, intent=intent)
            self._persist_branch(agent_id, branch)
            return {"deleted": True, "key": key, "branch_name": branch_name}

    def commit_branch(self, agent_id: str, branch_name: str) -> dict[str, Any]:
        with self._lock:
            branch = self._branch(agent_id, branch_name)
            snapshot = self.workspace.commit(agent_id, branch)
            self._db.execute(
                "DELETE FROM mcp_branches WHERE agent_id = ? AND branch_name = ?",
                (agent_id, branch_name),
            )
            self._db.commit()
            del self._branches[(agent_id, branch_name)]
            return {"committed": True, "head_version": snapshot.version_id, "state": snapshot.data}

    def acquire_lease(
        self, agent_id: str, resource_key: str, duration_seconds: float = 30.0
    ) -> dict[str, Any]:
        with self._lock:
            lease = self.workspace.acquire_lease(agent_id, resource_key, duration_seconds)
            return {
                "acquired": True,
                "resource_key": resource_key,
                "agent_id": agent_id,
                "expires_at": lease.expires_at,
            }

    def release_lease(self, agent_id: str, resource_key: str) -> dict[str, bool]:
        with self._lock:
            self.workspace.release_lease(agent_id, resource_key)
            return {"released": True}

    def get_events(self, limit: int = 50) -> list[dict[str, Any]]:
        if limit < 1 or limit > 1000:
            raise ValueError("limit must be between 1 and 1000")
        with self._lock:
            events = self.workspace.get_events()[-limit:]
            return [event.model_dump(mode="json") for event in events]

    @staticmethod
    def _validate_identity(agent_id: str, branch_name: str) -> None:
        if not agent_id.strip() or not branch_name.strip():
            raise ValueError("agent_id and branch_name must not be empty")
        if len(agent_id) > 128 or len(branch_name) > 128:
            raise ValueError("agent_id and branch_name must be 128 characters or fewer")

    def close(self) -> None:
        with self._lock:
            self.workspace.close()
            self._db.close()


def create_server(service: CohortService, host: str = "127.0.0.1", port: int = 8765) -> FastMCP:
    mcp = FastMCP("cerbere-cohort", host=host, port=port)

    @mcp.tool()
    def workspace_get_state() -> dict[str, Any]:
        """Return the current committed workspace state and HEAD version."""
        return service.get_state()

    @mcp.tool()
    def workspace_create_branch(agent_id: str, branch_name: str) -> dict[str, str]:
        """Create an isolated branch from the current HEAD before editing shared state."""
        return service.create_branch(agent_id, branch_name)

    @mcp.tool()
    def workspace_read_in_branch(agent_id: str, branch_name: str, key: str) -> dict[str, Any]:
        """Read one key from an agent's isolated branch."""
        return service.read_branch(agent_id, branch_name, key)

    @mcp.tool()
    def workspace_set_in_branch(
        agent_id: str, branch_name: str, key: str, value: Any, intent: str | None = None
    ) -> dict[str, Any]:
        """Write a JSON value to a branch. The write is persisted immediately."""
        return service.write_branch(agent_id, branch_name, key, value, intent)

    @mcp.tool()
    def workspace_delete_in_branch(
        agent_id: str, branch_name: str, key: str, intent: str | None = None
    ) -> dict[str, Any]:
        """Delete a key from a branch. The deletion is persisted immediately."""
        return service.delete_branch_key(agent_id, branch_name, key, intent)

    @mcp.tool()
    def workspace_commit(agent_id: str, branch_name: str) -> dict[str, Any]:
        """Commit a branch. Conflicting concurrent edits are rejected, never silently overwritten."""
        return service.commit_branch(agent_id, branch_name)

    @mcp.tool()
    def lease_acquire(
        agent_id: str, resource_key: str, duration_seconds: float = 30.0
    ) -> dict[str, Any]:
        """Acquire a time-limited lease on a shared resource."""
        return service.acquire_lease(agent_id, resource_key, duration_seconds)

    @mcp.tool()
    def lease_release(agent_id: str, resource_key: str) -> dict[str, bool]:
        """Release a lease owned by the calling agent."""
        return service.release_lease(agent_id, resource_key)

    @mcp.tool()
    def get_events(limit: int = 50) -> list[dict[str, Any]]:
        """Read the latest append-only coordination events."""
        return service.get_events(limit)

    return mcp


def main() -> None:
    parser = argparse.ArgumentParser(description="Cerbere Cohort MCP server")
    parser.add_argument(
        "--transport",
        choices=("streamable-http", "stdio"),
        default=os.getenv("COHORT_MCP_TRANSPORT", "streamable-http"),
    )
    parser.add_argument(
        "--db",
        default=os.getenv(
            "COHORT_DB_PATH", str(Path.home() / ".cerbere-cohort" / "workspace.db")
        ),
        help="SQLite database path (default: ~/.cerbere-cohort/workspace.db)",
    )
    parser.add_argument("--host", default=os.getenv("COHORT_MCP_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("COHORT_MCP_PORT", "8765")))
    args = parser.parse_args()

    service = CohortService(args.db)
    mcp = create_server(service, host=args.host, port=args.port)
    if args.transport == "stdio":
        mcp.run(transport="stdio")
    else:
        mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
