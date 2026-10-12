# Nimbus

A workspace for submitting, scheduling, and executing container workloads across connected workers. Nimbus now runs actual commands, retains their logs and output files, and reports their real outcomes.

![Nimbus overview](docs/screenshots/overview.jpg)

## Start locally

You need Docker Desktop (or Docker Engine with Compose), Python 3.10 or newer, and Make. Start Docker before continuing.

```sh
cp .env.example .env
openssl rand -hex 32
```

Put the generated value in `SECRET_KEY` in `.env`, then:

```sh
make dev
```

Open **http://localhost:5173**, create your administrator account, choose **New workload**, and submit the **Hello Nimbus** template. It prints five progress messages and produces `result.json`. Open the workload to watch its logs and download its result.

`make dev` builds and starts PostgreSQL, Redis, the API, the scheduler, and the frontend, applies database migrations, then starts a Docker execution agent on your host. The agent is essential: the scheduler containers assign work, while the host agent executes it. There is no Docker socket mounted into the API.

```sh
make agent       # Start the host agent if the stack is already running
make stop-agent  # Gracefully stop the host agent
make down        # Stop agent and services; preserve database volumes
make logs        # Inspect service logs
```

Host agent logs are in `.nimbus/worker.log`. Each agent runs one workload at a time. Use one agent per Docker daemon so advertised capacity is not counted twice.

## What you can do

- Inspect cluster capacity, queue activity, real execution success, and recent workloads.
- Submit a Python script or an explicit command argument array with a container image.
- Request CPU, RAM, GPU memory, priority, and a time limit.
- Search and filter paginated workloads, inspect their timeline, and revisit execution history.
- Watch retained logs, download logs and output files, cancel work, and retry an execution as a new job.
- Connect workers, inspect their heartbeats, and drain a worker before maintenance.
- Create member accounts. Members access their own workloads; administrators can manage the workspace.

The interface supports desktop and mobile layouts, keyboard navigation, loading and error states, live WebSocket updates, and polling when live updates are unavailable.

## Execution contract

The scheduler selects online, idle, compatible Docker workers in priority order, then creation order. CPU and RAM requests must fit the worker. GPU memory is an admission requirement against the largest detected GPU; it is not a hard VRAM quota. A CPU worker never receives a GPU workload.

Jobs move through `queued → assigned → running → completed/failed/cancelled`. Exit code zero means completed; a nonzero exit, execution error, timeout, or lost worker means failed. Cancellation of running work remains pending until the agent stops the container and confirms the outcome. A retry creates a separate linked execution, preserving history.

Containers receive CPU and RAM limits, a process limit, a read-only root filesystem, no network, dropped capabilities, and no extra host mounts beyond their temporary `/output` directory. They run as the agent's host UID/GID; run the agent as an ordinary user. Images must support that execution environment. Image downloads require host connectivity, and download time counts toward the execution timeout.

Write result files directly to `/output`. Nimbus collects up to eight regular files with safe filenames, at most 2 MiB each and 8 MiB total. Logs retain up to 1,000,000 characters. Nested directories and symlinks are not collected. Large model datasets, unrestricted network access, and large artifact storage are outside this version's execution contract.

## Connect another machine

On a machine with Python and a working Docker CLI, copy `backend/scripts/worker_agent.py`. Obtain the registration token from **Settings** as an administrator, store it in a private file, and run:

```sh
python3 worker_agent.py --name compute-01 \
  --api-url https://your-nimbus-host/api/v1 \
  --token-file /path/to/private-worker-token
```

Use a distinct worker name. For NVIDIA execution, the host also needs a working `nvidia-smi` and NVIDIA container support. This implementation passes `--gpus all` to Docker for GPU work; one job runs per agent. CPU execution was verified on this machine. GPU execution needs validation on actual NVIDIA hardware.

## Architecture and operations

React + TypeScript + Vite form the workspace. FastAPI serves authenticated APIs. PostgreSQL stores jobs, workers, accounts, logs, and bounded artifacts. Redis carries live events and Celery scheduling messages. Celery Beat triggers scheduling cycles; a host Python agent launches and supervises Docker containers.

- [Architecture and API](docs/architecture.md)
- [Illustrated project guide](docs/project-guide.md) — learn the implementation and rehearse a project presentation.
- [Editable Word handbook](docs/Nimbus_Project_Guide.docx)
- [Operation and deployment](docs/operations.md)
- [Verification results and limits](docs/verification.md)
- [Local scripts](scripts/README.md)

The production image path uses nginx to serve the built frontend and proxy API/WebSocket traffic on the same origin. `docker compose -f docker-compose.yml up --build` starts that stack on http://localhost:3000; start its host agent with `make agent`. Production images alone do not configure a public deployment. Public installations need HTTPS, protected credentials, backups, and deployment-specific configuration described in the operations guide.

## Development checks

```sh
make test-backend
make lint-backend
docker compose exec frontend npm test
make lint-frontend
docker compose exec frontend npm run build
```

Backend integration tests create and remove their own disposable PostgreSQL database, applying all migrations; they do not truncate your workspace database. Frontend tests cover submission validation and cancellation behavior. CI runs both suites, linting, type checks, and builds. Local frontend development outside Docker requires Node 22.22.2 or newer within Node 22, or a supported newer Node release.

Existing workspace records are preserved by migrations. Jobs created before real execution are identified as legacy records and excluded from the real execution success metric.
