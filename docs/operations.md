# Operations

## Local lifecycle

Use `make dev` to build/start services and the host execution agent. Migrations run automatically before the API starts. Readiness waits for PostgreSQL and Redis. All published service ports bind to `127.0.0.1`. `make down` preserves named data volumes; the next `make dev` restores the workspace.

Check `docker compose ps`, `docker compose logs backend celery-worker celery-beat`, and `.nimbus/worker.log` when a job does not start. The job detail page reports why a queued workload is waiting. Legacy workers are visible for history but never selected for execution.

To maintain a worker, drain it from **Workers**, wait for its active job to finish, then stop its agent. Draining prevents new assignments without interrupting its active container. An agent stopped during execution terminates the container and reports a failed or cancelled outcome.

## Configuration

| Setting | Purpose |
| --- | --- |
| `SECRET_KEY` | Random signing secret; use at least 32 random bytes |
| `ENVIRONMENT` | `local`, `test`, `staging`, or `production` |
| `SETUP_TOKEN` | First administrator setup secret required outside local mode |
| `WORKER_API_TOKEN` | Optional explicit registration secret; otherwise derived from `SECRET_KEY` |
| `BACKEND_CORS_ORIGINS` | Exact frontend origins, comma-separated or JSON list |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | User session lifetime, default one day |
| `WORKER_HEARTBEAT_TIMEOUT_SECONDS` | Default 45 seconds |
| `SCHEDULER_POLL_INTERVAL_SECONDS` | Default 5 seconds |
| `POSTGRES_*` | Database credentials and connection settings |

The bundled agent sends heartbeats every five seconds. Worker credentials last 30 days; restart/re-register before expiry. Reconnecting the same offline worker name replaces its old credential. Keep registration secrets private; any holder can enroll an execution worker.

## Production deployment

The production Compose path uses built frontend assets and nginx on port 3000, with API and WebSocket proxying under `/api/`. Keep same-origin routing when placing it behind an HTTPS ingress. Runtime frontend environment variables do not rewrite a compiled bundle; its default relative API paths work behind the proxy.

Before public use, set `ENVIRONMENT=production`, `DEBUG=false`, `LOG_LEVEL=INFO`, a random signing secret, a distinct setup token, database credentials, and the exact HTTPS frontend origin. Put the ingress on the same machine or a private network; the provided Compose bindings intentionally stay local. Production session cookies require HTTPS. Keep PostgreSQL, Redis, Flower, and pgAdmin private. The provided Flower and pgAdmin ports are local development/administration conveniences.

Back up PostgreSQL and test restoration, monitor readiness and failed/stale jobs, set retention/storage policies appropriate to the installation, and use trusted worker hosts. Account password reset, account deletion, token rotation UI, audit trails, automated database backups, multi-tenant quotas, and object storage are not implemented in this release. Treat it as a capable local/internal workspace, and assess those requirements for a public service.

## Execution boundaries

CPU and RAM are Docker limits; GPU memory is admission only. One worker represents one Docker daemon and executes one container at a time. Multi-GPU device allocation and parallel capacity packing are future extensions. Avoid registering multiple agents against the same Docker daemon: Nimbus does not deduplicate physical host capacity.

Containers have no runtime network access. They cannot fetch datasets or packages; bake dependencies into their image. Docker images and the host agent must support the host's architecture. Use compatible images on Apple Silicon. NVIDIA execution needs a supported Linux GPU host with the NVIDIA container runtime; macOS Docker Desktop is a CPU worker here.

Logs and artifacts live in PostgreSQL with per-job bounds. There is no automatic retention cleanup or cluster-wide disk quota. Keep output small, and plan storage before long-running unattended use.
