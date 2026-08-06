# Nimbus — AI Workload Scheduling and GPU Resource Management Platform

Nimbus is a cloud-inspired platform for submitting AI workloads, scheduling
them onto available GPU workers, and observing the whole system through a
live dashboard: queue status, worker utilization, logs, and execution
history.

This repository currently contains the **project scaffold**: architecture,
tooling, and infrastructure wiring. Business logic (the scheduler,
workload lifecycle, worker registration/heartbeats, log streaming) is
intentionally not yet implemented — see [Roadmap](#roadmap).

## Architecture

```
                        ┌─────────────┐
                        │   Frontend   │  React + TS + Tailwind (Vite)
                        │  (nginx/SPA) │
                        └──────┬──────┘
                               │ REST (Axios) / WS
                               ▼
                        ┌─────────────┐        ┌──────────────┐
                        │   Backend    │◄──────►│  PostgreSQL   │
                        │  (FastAPI)   │        └──────────────┘
                        └──────┬──────┘
                               │
                 ┌─────────────┼─────────────┐
                 ▼             ▼             ▼
           ┌──────────┐ ┌────────────┐ ┌────────────┐
           │  Redis   │ │  Celery    │ │   Flower    │
           │ (broker) │ │  worker(s) │ │ (monitoring)│
           └──────────┘ └────────────┘ └────────────┘
```

- **FastAPI** serves the versioned REST API (`/api/v1`), with async
  SQLAlchemy for data access and Pydantic for request/response contracts.
- **PostgreSQL** is the system of record for workloads, workers, and
  execution history.
- **Redis** backs both the Celery broker/result-backend and future
  caching/pub-sub needs (e.g. live queue updates).
- **Celery** runs background work — scheduling decisions, workload
  execution orchestration, and periodic housekeeping (via `beat`).
- **React + TypeScript + Tailwind** renders the operator-facing dashboard,
  talking to the API through a typed Axios client and TanStack Query.
- **Docker Compose** wires all of the above together for local
  development and as a template for production deployment.

## Tech stack

| Layer            | Technology                                      |
|-------------------|--------------------------------------------------|
| API               | FastAPI, Pydantic v2, async SQLAlchemy 2.0        |
| Database          | PostgreSQL 16, Alembic migrations                 |
| Cache / broker    | Redis 7                                           |
| Background jobs   | Celery 5 (worker + beat), Flower for monitoring   |
| Frontend          | React 18, TypeScript, Vite, Tailwind CSS          |
| Frontend data     | TanStack Query, Axios, Zustand                    |
| Containerization  | Docker, Docker Compose                            |

## Project layout

```
nimbus/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app factory / entrypoint
│   │   ├── core/                # settings, logging, security primitives
│   │   ├── db/                  # SQLAlchemy engine, session, declarative base
│   │   ├── models/               # ORM models (empty — scaffolding only)
│   │   ├── schemas/               # Pydantic schemas (empty — scaffolding only)
│   │   ├── api/v1/                # versioned routers (health check implemented)
│   │   ├── services/               # business logic layer (empty)
│   │   ├── workers/                # Celery app + task modules (empty)
│   │   └── tests/                  # pytest suite (health check test included)
│   ├── alembic/                    # migration environment
│   ├── requirements.txt / requirements-dev.txt
│   └── Dockerfile                  # multi-stage: development / production
├── frontend/
│   ├── src/
│   │   ├── main.tsx / App.tsx      # app bootstrap + route table
│   │   ├── components/layout/       # AppShell, Sidebar, Topbar
│   │   ├── components/common/       # PageHeader, EmptyState
│   │   ├── pages/                   # Dashboard, Queue, Workers, History, Logs
│   │   ├── api/                     # Axios client
│   │   ├── hooks/                   # TanStack Query hooks
│   │   ├── store/                   # Zustand stores
│   │   └── types/                   # shared TS types
│   ├── package.json
│   └── Dockerfile                   # multi-stage: development / nginx production
├── docker-compose.yml               # all services, production-targeted by default
├── docker-compose.override.yml      # dev overrides: hot reload, pgAdmin (auto-loaded)
├── .env.example
└── Makefile                         # convenience commands
```

## Getting started

### Prerequisites

- Docker and Docker Compose v2
- (Optional, for running things outside Docker) Python 3.12+ and Node 22+

### 1. Configure environment

```bash
cp .env.example .env
# Generate a real secret key:
openssl rand -hex 32   # paste the result into SECRET_KEY in .env
```

### 2. Start the stack (development mode)

```bash
docker compose up --build
# or: make up
```

This builds every service from its `development` target with hot reload
and bind-mounted source, and starts:

| Service       | URL                              |
|---------------|-----------------------------------|
| Frontend      | http://localhost:5173             |
| Backend API   | http://localhost:8000              |
| API docs      | http://localhost:8000/api/v1/docs  |
| Flower        | http://localhost:5555/flower       |
| pgAdmin       | http://localhost:5050               |

### 3. Run database migrations

No models exist yet, so there's nothing to migrate — but once models are
added:

```bash
make migrate-new msg="add workloads table"
make migrate
```

### Running a production-like build

```bash
docker compose -f docker-compose.yml up --build
# or: make up-prod
```

This uses each service's `production` target — a compiled, non-root
backend image and an nginx-served static frontend build.

## Backend development (outside Docker, optional)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

Run tests / linting:

```bash
pytest
ruff check .
mypy .
```

## Frontend development (outside Docker, optional)

```bash
cd frontend
npm install
npm run dev
```

Lint / type-check:

```bash
npm run lint
npm run type-check
```

## Roadmap

This scaffold intentionally stops short of business logic. Planned next
steps, in rough order:

1. **Data model** — `Workload`, `GPUWorker`, `QueueEntry`, `ExecutionRecord`
   SQLAlchemy models + Alembic migration, plus matching Pydantic schemas.
2. **Workload submission API** — create/list/cancel workloads.
3. **Worker registration & heartbeats** — GPU workers register capacity
   and report liveness; readiness reflected in `/ready`.
4. **Scheduler** — Celery task that matches queued workloads to available
   GPU capacity and dispatches execution.
5. **Execution tracking & log capture** — status transitions, timing, and
   captured stdout/stderr per workload.
6. **Dashboard wiring** — replace the empty-state pages with live data via
   the hooks/query layer already in place.
7. **Auth** — real login flow on top of the existing JWT/password
   utilities in `app.core.security` and the `useAuthStore` shell.
8. **Observability** — structured logs already in place; add
   metrics/tracing as the scheduler comes online.
