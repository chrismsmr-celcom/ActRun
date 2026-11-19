# Self-host Cohort (Community)

The self-hosted Community path runs the FastAPI adapter with local SQLite. It is intended for evaluation and a single trusted machine. The current SQLite API mode bypasses hosted authentication, so keep it bound to localhost; do not expose it directly to the public internet.

## Requirements

- Docker Engine and Docker Compose plugin
- A machine with persistent disk space for the SQLite volume

## Start

From the repository root:

```bash
docker compose up --build -d
docker compose logs -f cohort
```

The API listens at `http://127.0.0.1:8000`:
- Health: `http://127.0.0.1:8000/api/health`
- OpenAPI: `http://127.0.0.1:8000/docs`

The named Docker volume `cohort-data` persists the SQLite database across container restarts and image upgrades.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `COHORT_DB_PATH` | `/data/cohort.db` in Compose | SQLite database path |
| `COHORT_REQUIRE_LEASES` | `true` in Compose | Require a lease before branch writes |
| `COHORT_TELEMETRY` | `false` | Explicit opt-in to anonymous installation heartbeat |
| `COHORT_TELEMETRY_URL` | empty | URL of the Cohort telemetry collector; required only when opted in |

Telemetry is disabled by default. If enabled, Cohort sends an installation UUID, Cohort version, and deployment type. It does not send prompts, agent names, workspace keys/values, project files, credentials, or host identifiers. The UUID is stored in the container user's config directory; to keep it stable across container recreation, mount a persistent home directory or set `COHORT_TELEMETRY_ID_PATH` to a path on a persistent volume. The collector may see the network request's source IP in infrastructure logs; Cohort's telemetry payload does not include it.

To opt in, set `COHORT_TELEMETRY=true` and `COHORT_TELEMETRY_URL=https://YOUR-COHORT-API/api/telemetry/install`. If the collector is unreachable, the local API continues operating. You can opt out at any time by setting `COHORT_TELEMETRY=false`.

## Stop, upgrade, and backup

```bash
docker compose down
docker compose pull
docker compose up --build -d
```

The named volume is not removed by `docker compose down`. To back up the SQLite database, stop the service and copy the volume contents using your Docker volume backup procedure. Do not delete the volume unless you intend to delete local Cohort state.

## Security boundary

This Community configuration is local-only and has no user authentication. Do not change the port binding to `0.0.0.0` or put it behind a public reverse proxy. Public, multi-user self-hosting requires organization-scoped authorization, hardened deployment configuration, and a supported shared database workflow that are not yet complete.
