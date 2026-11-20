# SaaS deployment (early beta)

This guide deploys the existing hosted REST API and React dashboard. It does not turn the current API into a generally multi-tenant or horizontally scalable service.

## Architecture

- **Frontend:** Vercel (React/Vite dashboard).
- **API:** one Render web-service instance.
- **Database:** one PostgreSQL database, preferably the Supabase project's database already used for authentication.
- **Authentication:** Supabase Auth access tokens, verified by the API. Do not put a Supabase service-role key in the browser.

Do not configure a second, unrelated Render database while assuming it shares Supabase Auth data. The API's membership check reads `public.cohort_memberships` from the same `DATABASE_URL`.

## 1. Database and membership

Create a Supabase project and use its PostgreSQL connection string as the API's `DATABASE_URL`. Use a connection string compatible with psycopg 3; the adapter disables prepared statements for pooler compatibility.

The current API expects a table named `public.cohort_memberships` with:
- `organization_id` (UUID)
- `user_id` (UUID)
- `role` (text: `owner`, `admin`, or `member`)
- `status` (text; active members use `active`)

The organization ID must be a UUID and must match `COHORT_ORGANIZATION_ID`. The API currently supports one configured organization per deployment. Configure membership creation and management separately; this repository does not yet provide a complete organization-admin workflow.

## 2. Deploy the API on Render

Create a **Web Service** from this repository:

| Setting | Value |
| --- | --- |
| Runtime | Python |
| Root directory | `python` |
| Build command | `pip install ".[postgres]"` |
| Start command | `uvicorn cerbere_cohort.api:app --host 0.0.0.0 --port $PORT` |
| Health check path | `/api/health` |
| Instances | One |

Set these environment variables:

| Variable | Value |
| --- | --- |
| `DATABASE_URL` | Supabase PostgreSQL connection string |
| `SUPABASE_URL` | Supabase project URL |
| `COHORT_ORGANIZATION_ID` | UUID of the one enabled organization |
| `COHORT_CORS_ORIGINS` | Exact Vercel frontend origin, e.g. `https://your-app.vercel.app` |
| `COHORT_ENV` | `production` |
| `COHORT_REQUIRE_LEASES` | `true` if writes must hold a lease |\n| `COHORT_TELEMETRY_COLLECTOR_ENABLED` | `true` only if accepting opt-in self-hosted installation pings |

Do not set `COHORT_CORS_ORIGINS=*` in hosted PostgreSQL mode. Render provides `PORT`; do not hard-code it.

To receive opt-in Community installation pings, set `COHORT_TELEMETRY_COLLECTOR_ENABLED=true`. This creates the aggregate telemetry table at API startup. Keep it unset to disable collection. Authenticated workspace members can then read aggregate counts from `/api/traction`.\n\nAfter deployment, check `/api/health`. It should report PostgreSQL persistence and Supabase authentication. A successful health check does not prove membership queries or all database operations work; inspect logs and run an authenticated end-to-end test.

## 3. Deploy the dashboard on Vercel

Import the same repository and configure the frontend root/build settings for the `web` Vite app (build command `npm run build`, output directory `dist`).

Set the frontend environment variables:

- `VITE_API_BASE_URL`: public Render API URL.
- `VITE_SUPABASE_URL`: Supabase project URL.
- `VITE_SUPABASE_ANON_KEY`: Supabase publishable/anon key only.
- `VITE_COHORT_ORGANIZATION_ID`: enabled organization UUID.

Never use `service_role` or any server secret in a `VITE_*` variable. Vite embeds these values into public browser assets.

## 4. Configure Supabase Auth URLs

In Supabase Auth URL configuration:
- Site URL: your Vercel production origin.
- Redirect URLs: the exact production origin and your local development origin (for example, `http://localhost:5173/**`).

Use the production Vercel URL in Render's `COHORT_CORS_ORIGINS`.

## 5. Verify the deployment

1. Open `https://YOUR-API/api/health`; confirm PostgreSQL and Supabase are reported.
2. Open `https://YOUR-API/docs`; inspect the actual OpenAPI schemas.
3. Sign in through the dashboard.
4. Confirm a non-member receives 403 and an active member can read workspace state.
5. Create two branches, make conflicting writes, and confirm the second commit reports a conflict rather than silently overwriting the first.
6. Restart the API and confirm persisted branches and workspace state are restored.

## Current operational limits

- One organization per API deployment.
- One API instance only; do not scale horizontally.
- MCP has a separate branch registry and is not a remote authenticated multi-user service.
- No agent-level identity or external-tool authorization.
- PostgreSQL integration must be validated against the actual Supabase project before production use.

Treat this as an early-beta deployment, not an enterprise-ready multi-tenant architecture.
