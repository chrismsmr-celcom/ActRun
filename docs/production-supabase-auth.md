# Supabase authentication and workspace bootstrap

## Production API environment (Render)

Set these variables in the Cohort API service:

- `DATABASE_URL`: Supabase PostgreSQL connection string. Use the pooler connection appropriate for a long-running API if required by your Supabase plan.
- `SUPABASE_URL`: project URL, for example `https://<project-ref>.supabase.co`.
- `COHORT_ORGANIZATION_ID`: UUID of the one organization enabled on this deployment.
- `COHORT_CORS_ORIGINS`: exact Vercel origin(s), comma-separated, e.g. `https://cohort-delta.vercel.app`.
- `COHORT_REQUIRE_LEASES`: `true` or `false`.

The API fails at startup if `DATABASE_URL`, `SUPABASE_URL`, or `COHORT_ORGANIZATION_ID` is malformed/missing for production. The backend verifies Supabase asymmetric JWTs through the project's JWKS endpoint and checks an active row in `public.cohort_memberships` on every API request. It does not trust a role or organization claim supplied by the browser.

## Apply the database migration

Run `supabase/migrations/202611190001_cohort_organizations.sql` in the Supabase SQL Editor.

Create the first organization:

```sql
insert into public.cohort_organizations (name)
values ('Your organization')
returning id;
```

Copy the returned UUID into Render's `COHORT_ORGANIZATION_ID`.

Create the first owner membership after the owner has signed up through Supabase Auth:

```sql
insert into public.cohort_memberships (organization_id, user_id, role, status)
values (
  '<COHORT_ORGANIZATION_ID>',
  '<AUTH_USERS_ID>',
  'owner',
  'active'
);
```

Find the user UUID in Supabase Dashboard → Authentication → Users. Provision additional memberships through trusted admin tooling or the SQL Editor, not through the public browser client.

## Frontend environment (Vercel)

Set:

- `VITE_API_BASE_URL`: Render API base URL, with no trailing slash.
- `VITE_SUPABASE_URL`: same Supabase project URL.
- `VITE_SUPABASE_ANON_KEY`: Supabase publishable/anon key only.
- `VITE_COHORT_ORGANIZATION_ID`: same organization UUID configured on Render.

Never put the Supabase service-role key or PostgreSQL password in Vercel's `VITE_*` variables or browser code.

The dashboard supports email magic links and Google sign-in. Enable Google as a provider in Supabase Auth and configure its OAuth credentials and redirect URLs in the Supabase dashboard. Add the Vercel production URL and any preview URLs you actually use to Supabase Auth's allowed redirect URLs.

## Current security boundary

This release intentionally supports **one organization per API deployment**. The API rejects any other organization ID and verifies active membership on every route except the public health check. Roles `owner`, `admin`, and `member` can write; `viewer` is read-only.

This is not yet a shared multi-tenant control plane: organization-scoped data partitioning across multiple organizations, organization-aware branch records, and cross-instance branch locking still need implementation and integration tests. Do not put multiple customer organizations behind one instance until those changes land.

Remote MCP over HTTP is deliberately blocked when `DATABASE_URL` is configured because authenticated MCP transport has not been implemented. Use local stdio integration only. REST and MCP persist to the same database schema, but their in-memory engine caches are not yet coordinated across separate processes; avoid simultaneous API/MCP writes to the same workspace until a shared runtime/service boundary is implemented.
