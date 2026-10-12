.PHONY: up up-prod down build logs ps \
        migrate migrate-new shell-backend shell-db \
        test-backend lint-backend format-backend \
        test-frontend lint-frontend format-frontend

# --- Stack lifecycle ---
up:            ## Start the full stack in dev mode (hot reload)
	docker compose up --build

up-prod:       ## Start the full stack using production images
	docker compose -f docker-compose.yml up --build

down:          ## Stop the local worker and containers; retain database volumes
	python3 scripts/local.py down

build:         ## Rebuild all images
	docker compose build

logs:          ## Tail logs for all services
	docker compose logs -f

ps:            ## List running services
	docker compose ps

# --- Database ---
migrate:       ## Apply Alembic migrations
	docker compose exec backend alembic upgrade head

migrate-new:   ## Generate a new Alembic revision, e.g. `make migrate-new msg="add workloads table"`
	docker compose exec backend alembic revision --autogenerate -m "$(msg)"

shell-backend: ## Open a shell in the backend container
	docker compose exec backend bash

shell-db:      ## Open a psql shell against the postgres container
	docker compose exec postgres psql -U nimbus -d nimbus

# --- Backend quality ---
test-backend:
	docker compose exec backend pytest

lint-backend:
	docker compose exec backend ruff check .

format-backend:
	docker compose exec backend ruff format .

# --- Frontend quality ---
test-frontend:
	docker compose exec frontend npm test

lint-frontend:
	docker compose exec frontend npm run lint

format-frontend:
	docker compose exec frontend npm run format

# Start the stack, then execute jobs through a local Docker worker.
.PHONY: dev agent
dev:
	python3 scripts/local.py up

agent:
	python3 scripts/local.py agent

.PHONY: stop-agent
stop-agent:
	python3 scripts/local.py stop-agent
