# Traction measurement

Cohort tracks three different signals. They must not be added together or described as users.

| Signal | Source | What it means | What it does not mean |
| --- | --- | --- | --- |
| Git clones / unique cloners | GitHub repository Traffic API | Repository download activity | People, installations, or active users |
| Self-hosted installations | Explicit opt-in telemetry | Distinct installation IDs reporting recently | Verified customers or unique people |
| SaaS usage | Authenticated product activity | Actual accounts and workspace activity | Automatically paid customers |

## GitHub clone archive

GitHub exposes clone and view statistics for a rolling 14-day window. The scheduled workflow archives daily snapshots in `metrics/github-traffic.json`; the file therefore provides a historical series beyond GitHub's rolling window.

Add a repository Actions secret named `COHORT_TRAFFIC_TOKEN`. It must be a fine-grained token scoped to this repository with read access to repository traffic (GitHub currently exposes this through repository administration read permission). The workflow uses the normal Actions token to commit the resulting JSON history.

Run the workflow manually once from Actions to verify permissions. The daily schedule is UTC. If the secret is missing or lacks traffic permission, the collection job fails rather than silently writing zeroes.

## Opt-in self-hosted telemetry collector

The hosted API must have PostgreSQL configured and `COHORT_TELEMETRY_COLLECTOR_ENABLED=true`. It creates a small table containing installation UUID, version, deployment type, first-seen timestamp, and last-seen timestamp.

Self-hosted operators must explicitly set:
- `COHORT_TELEMETRY=true`
- `COHORT_TELEMETRY_URL=https://YOUR-COHORT-API/api/telemetry/install`

The authenticated SaaS endpoint `GET /api/traction` reports total installation IDs, IDs seen in the last 30 days, and version counts. It is an aggregate operational endpoint, not a public dashboard.

Installation telemetry is voluntary and self-reported. A user can generate multiple IDs, disable telemetry, or submit a fabricated ID. Use it as a directional adoption signal, not an audited metric. Never describe a clone as an installation or an installation as a customer.

## SaaS metrics to add as product instrumentation

The current dashboard should eventually report:
- accounts created and activated;
- organizations with at least one active member;
- weekly active users;
- workspaces with at least two agents;
- branches created and committed;
- conflict rate and conflict resolution rate;
- retention by signup cohort;
- trial-to-paid conversion once billing exists.

Do not infer these metrics from GitHub clones. Add product events only after defining event semantics and a retention policy.
