# Cohort dashboard

React + Vite control plane for the Cohort runtime. Design system: Manrope + Roboto (self-hosted via @fontsource), 8-point spacing, opaque cards over a grid/grain background, light and dark themes.

## Run the dashboard locally

Terminal 1 — start the Python runtime API from the repository root:

```powershell
python -m pip install -e .\python
$env:COHORT_DB_PATH = ".\data\cohort.db"
cerbere-cohort-api
```

The API listens on `http://127.0.0.1:8000`.

Terminal 2 — start Vite:

```powershell
cd web
npm install
npm run dev
```

Vite proxies `/api` requests to `http://127.0.0.1:8000`. To use another local API host, set `COHORT_API_PROXY` before starting Vite.

For a separately hosted API, configure `VITE_API_URL` at build time to the API origin, for example `https://your-api.example.com`. The API must allow that dashboard origin through `COHORT_CORS_ORIGINS`.

## API endpoints

- `GET /api/health`
- `GET /api/overview`
- `GET /api/branches`, `POST /api/branches`
- `PUT /api/branches/{id}/state`
- `POST /api/branches/{id}/commit`
- `POST /api/branches/{id}/resolve`
- `GET /api/state`
- `GET /api/events?limit=100`
- `GET /api/leases`, `POST /api/leases`, `DELETE /api/leases/{key}?agent_id=...`
- `GET /api/settings`

## Endpoints the UI already expects (not implemented in the API yet)

Each one is optional: on 404/405/501 the screen shows an honest "not connected" state, never sample data.

| Screen | Request | Response |
| --- | --- | --- |
| Gateway | `GET /api/gateway/agents` | `{ items: { id, name, kind, status: "connected"\|"idle"\|"error"\|"disconnected", last_seen, endpoint?, version? }[] }` |
| Gateway | `POST /api/gateway/agents` | body `{ name, kind, endpoint? }` → the created agent |
| Performance | `GET /api/performance` | `{ window_seconds, api: { p50_ms, p95_ms, p99_ms, error_rate, requests_per_min }, series[], endpoints[], agents[], incidents[] }` |
| Advisor | `GET /api/advisor` | `{ items: { id, severity: "info"\|"warning"\|"critical", title, detail, action?: { label, tab?, href? } }[] }` |
| Cerbère AG | `GET /api/cerbere/summary?window=24h\|7d\|30d` | `{ window, totals: { blocked, flagged, allowed }, by_rule[], items: { id, timestamp, agent_id, decision, rule, target, reason }[] }` |
| Update Plan | `GET /api/billing/plans`, `POST /api/billing/checkout` | `{ current?, plans: { id, name, description, price?, period?, features?, cta? }[] }` / `{ url }` |

TypeScript contracts: `src/lib/types.ts`. Advisor also computes recommendations locally from live data, and Performance measures real request latency in the browser.

## Navigation and shortcuts

Hash routes (`#/branches`), `Ctrl/⌘ + K` or `/` for search, sidebar modes (expanded, expand on hover, collapsed) saved in `localStorage`.

## Important runtime limitations

This is an integration adapter for the existing Python coordination core, not a claim that Cohort is already a production multi-user service.

- The Python core persists snapshots, objects, events and leases in SQLite.
- The HTTP adapter currently keeps branch handles and its branch registry in process memory. Open branches are therefore lost on API restart.
- Run one API process only. Multi-process or multi-host coordination is not supported by this adapter.
- Authentication, authorization, tenant isolation, rate limiting and CSRF protections are not implemented. Do not expose this API to the public internet or connect it to sensitive workspaces until those controls are added.
- The MCP server remains a separate local stdio prototype.

The dashboard polls the API every five seconds. It does not silently replace failed API responses with fabricated sample values. When the API is unavailable, the dashboard shows a disconnected state.
