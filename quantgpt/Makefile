.PHONY: help up down build rebuild logs ps health migrate migrate-new backend-shell frontend-shell test lint fmt clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

up: ## Start all services (build if needed)
	docker compose up -d --build

down: ## Stop all services
	docker compose down

build: ## Build images
	docker compose build

rebuild: ## Rebuild without cache
	docker compose build --no-cache

logs: ## Tail logs
	docker compose logs -f --tail=100

ps: ## List services
	docker compose ps

health: ## Hit backend health endpoint
	@curl -fsS http://localhost:8000/health | python3 -m json.tool || echo "backend not reachable"

migrate: ## Apply Alembic migrations
	docker compose exec backend alembic upgrade head

migrate-new: ## Create a new Alembic migration (usage: make migrate-new m="msg")
	docker compose exec backend alembic revision --autogenerate -m "$(m)"

backend-shell: ## Shell into backend
	docker compose exec backend bash

frontend-shell: ## Shell into frontend
	docker compose exec frontend sh

test: ## Run backend tests
	docker compose exec backend pytest -v

lint: ## Lint backend + frontend
	docker compose exec backend ruff check .
	docker compose exec frontend npm run lint

fmt: ## Format backend
	docker compose exec backend ruff format .

clean: ## Remove containers, volumes, orphans
	docker compose down -v --remove-orphans
