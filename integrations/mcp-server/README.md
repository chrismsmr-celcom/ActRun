# Cerbere Cohort MCP Server

Cerbere Cohort exposes shared workspace coordination to MCP-compatible coding
agents. Run **one server process** and connect multiple clients to the same
Streamable HTTP endpoint. The server serializes workspace mutations and stores
committed state, leases, events, and open branches in SQLite.

## What it provides

- Shared committed workspace state and versioned HEAD.
- Isolated branches per `agent_id` and `branch_name`.
- Branch reads, writes, and deletes.
- Conflict-aware commits: overlapping edits are rejected rather than silently
  overwriting another agent's changes; disjoint edits can merge.
- SQLite persistence, including unfinished branch state across server restarts.
- Resource leases with renewal, fencing tokens, and an append-only event log.
- Streamable HTTP for multiple clients, plus stdio for single-client setups.

## Requirements

- Python 3.10+
- An MCP-compatible client
- One local checkout of this repository

## Install from the repository root

Install the Python library and MCP server in editable mode:

```bash
python -m pip install -e ./python
python -m pip install -e ./integrations/mcp-server
```

## Start the local development server

```bash
cerbere-cohort-mcp --transport streamable-http
```

Default endpoint:

```text
http://127.0.0.1:8765/mcp
```

The default database is `~/.cerbere-cohort/workspace.db`. Configure it with
`COHORT_DB_PATH` or `--db`.

Useful options:

```bash
cerbere-cohort-mcp --help
cerbere-cohort-mcp --db ./data/cohort.db --host 127.0.0.1 --port 8765
```

Keep the server running while clients are connected. Point Cursor, Codex,
Mistral Code, or another MCP client at the same endpoint. Client configuration
syntax varies; use its Streamable HTTP MCP transport and the URL above.

**Security boundary:** local Streamable HTTP remains unauthenticated and must stay on loopback. Do not expose it to a LAN, public interface, or the internet.

For production PostgreSQL deployments, run one stdio server process per agent and set these environment variables:

- `DATABASE_URL`: PostgreSQL connection string.
- `COHORT_ORGANIZATION_ID`: organization UUID; the MCP branch registry is stored in that organization's schema.
- `COHORT_MCP_AGENT_ID`: immutable agent identity bound to that process. Calls that claim another `agent_id` are rejected.

Production MCP mode requires a bound agent identity and enables lease enforcement. Each branch write must hold a lease for the key being changed. `lease_acquire` returns a monotonically increasing `fencing_token`; same-owner renewal extends expiry without changing the token, while takeover after expiry receives a higher token. Commits reject expired or superseded tokens. Event reads are filtered to the bound agent. `workspace_get_state` intentionally exposes the shared committed state to the connected agent because that is Cohort's coordination model.

## MCP tools

| Tool | Purpose |
| --- | --- |
| `workspace_get_state` | Read committed state and HEAD version |
| `workspace_create_branch` | Create an isolated branch |
| `workspace_read_in_branch` | Read a key from a branch |
| `workspace_set_in_branch` | Set a JSON value in a branch |
| `workspace_delete_in_branch` | Delete a key in a branch |
| `workspace_commit` | Commit a branch with conflict detection |
| `lease_acquire` | Acquire a time-limited resource lease |
| `lease_release` | Release a lease owned by an agent |
| `get_events` | Read recent coordination events |

### Recommended agent workflow

1. Choose a stable, unique `agent_id` (for example, `cursor` or `codex`).
2. Create a branch before editing shared state.
3. Read the keys you intend to change.
4. Write changes to that branch; do not write directly to HEAD.
5. Commit when the work is ready.
6. If the commit reports a conflict, read the latest HEAD and reconcile
   explicitly. Do not blindly retry with stale values.

Example tool sequence:

```text
workspace_create_branch(agent_id="cursor", branch_name="auth-refactor")
workspace_read_in_branch(agent_id="cursor", branch_name="auth-refactor", key="architecture")
workspace_set_in_branch(agent_id="cursor", branch_name="auth-refactor", key="architecture", value={"owner": "cursor"})
workspace_commit(agent_id="cursor", branch_name="auth-refactor")
```

## Stdio mode

Stdio starts an independent server process and is suitable for one MCP client.
It does **not** provide shared state between separate client-launched processes.

```bash
cerbere-cohort-mcp --transport stdio
```

For coordination between multiple agents, use one shared Streamable HTTP server.

## Current scope and limitations

- Local SQLite mode is intended for one server process on one machine.
- Production PostgreSQL mode supports separate stdio server processes per agent, sharing the same organization schema; database transactions and fencing tokens coordinate their writes.
- It is not a multi-region coordination service.
- Local unauthenticated HTTP is for loopback development only. Production MCP identity is process-bound; remote authenticated HTTP transport is not enabled yet.
