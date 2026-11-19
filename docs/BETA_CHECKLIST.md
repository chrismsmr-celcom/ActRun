# Beta launch checklist

Work through this top to bottom once per environment. Every item has bitten a first deployment.

## Supabase
- [ ] Apply `supabase/migrations/202611190001_cohort_organizations.sql` in the SQL editor.
- [ ] Insert one organization, then one `cohort_memberships` row (`role`, `status = 'active'`) per tester. Testers without a row see "not an active member".
- [ ] The API verifies tokens with the project's **asymmetric** JWT signing keys (ES256/RS256, via JWKS). If the project still uses the legacy shared HS256 secret, every request returns 401 — rotate to asymmetric signing keys first.
- [ ] Auth -> URL Configuration: add the dashboard origin to **Site URL** and **Redirect URLs**, otherwise magic links bounce to localhost.
- [ ] Use the **direct** or **session-pooler** connection string for `DATABASE_URL` (the runtime uses advisory locks and a long-lived connection; transaction-pooler mode can break both).

## API (Render)
- [ ] Env: `DATABASE_URL`, `SUPABASE_URL`, `COHORT_ORGANIZATION_ID`, `COHORT_CORS_ORIGINS` (exact dashboard origin, no `*`), `COHORT_ENV=production`. The API now refuses to boot on a hosted platform without `DATABASE_URL`, so a forgotten variable can no longer expose an open API.
- [ ] Keep **one instance** (state is held in memory and replayed from Postgres at boot).
- [ ] Free plan sleeps when idle: switch to `starter` before inviting testers.
- [ ] `GET /api/health` returns `"authentication": "supabase"` (not `development-bypass`).

## Dashboard (Vercel/Netlify/static host)
- [ ] Set the `VITE_*` variables from `web/.env.example` as **build-time** variables and redeploy.
- [ ] Sign in with a non-member account (expect a clear 403), then with a member account.
- [ ] Walk the golden path: create branch -> **Write** a key -> merge -> see the event; then force a conflict from two branches and resolve it.

## Known limits to tell testers
- Single organization per deployment; authenticated hosted MCP is not available yet.
- Any writer can act as any `agent_id` (agent identity is not bound to the user).
- Membership changes take up to 30 s to apply (`COHORT_MEMBERSHIP_CACHE_SECONDS`).
