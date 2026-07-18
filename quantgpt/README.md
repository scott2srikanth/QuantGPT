# QuantGPT

QuantGPT is an AI-assisted algorithmic trading intelligence layer that integrates with [OpenAlgo](https://github.com/marketcalls/openalgo) through a dedicated **Integration Layer** — it never modifies OpenAlgo's core. QuantGPT owns the cognitive surface (conversation, signals, strategy scoring, explainability); OpenAlgo remains the trading authority.

> This repository contains **project infrastructure only** — no AI and no trading logic yet. It compiles and runs end-to-end with Docker Compose.

## Architecture

```
┌──────────────────── QuantGPT (this repo) ────────────────────┐
│                                                              │
│  Next.js 15 frontend ── HTTP ──► FastAPI backend             │
│                                   │                          │
│        ┌──────────────────────────┼─────────────────────┐    │
│        │  PostgreSQL   Redis      │  Alembic   Logging   │    │
│        └──────────────────────────┴─────────────────────┘    │
│                                   │                          │
│                            Integration Layer                 │
│                                   │  REST / WS / EventBus    │
└───────────────────────────────────┼──────────────────────────┘
                                    ▼
                          OpenAlgo (unmodified)
```

### Principles

- **Never modify OpenAlgo.** All access goes through the Integration Layer (`backend/app/integration/`), which talks to OpenAlgo's REST `/api/v1`, WebSocket proxy (port 8765), and MCP server as an external client.
- **QuantGPT owns its own data** in PostgreSQL (conversation, signals, scores). OpenAlgo stays the source of truth for orders, positions, and market data.
- **Additive only.** OpenAlgo's EventBus subscribers, blueprints, and services are never edited; QuantGPT listens as a client.

## Repository layout

```
quantgpt/
├── backend/                 # FastAPI service
│   ├── app/
│   │   ├── api/v1/          # REST routers (auth, users, health, integration)
│   │   ├── auth/            # JWT + role management
│   │   ├── config/          # Pydantic settings
│   │   ├── core/            # DI container, lifespan
│   │   ├── db/              # SQLAlchemy engine/session, base model
│   │   ├── integration/     # OpenAlgo client (REST + WS)
│   │   ├── logging/        # Structured logging
│   │   ├── models/          # SQLAlchemy ORM models
│   │   ├── schemas/         # Pydantic request/response schemas
│   │   ├── services/        # Business logic (DI)
│   │   ├── workers/         # Background workers (Redis-backed)
│   │   └── main.py
│   ├── alembic/             # Migrations
│   ├── tests/
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── alembic.ini
├── frontend/                # Next.js 15 app (App Router, TypeScript)
│   ├── src/
│   │   ├── app/             # Routes
│   │   ├── components/
│   │   ├── lib/             # API client, auth
│   │   └── types/
│   ├── Dockerfile
│   └── package.json
├── packages/
│   └── shared-types/        # Shared TypeScript types (frontend ↔ future SDKs)
├── infra/
│   ├── postgres/init.sql
│   └── redis/redis.conf
├── docker-compose.yml
├── .env.example
├── Makefile
└── README.md
```

## Quick start

```bash
cp .env.example .env
make up            # build + start postgres, redis, backend, frontend
make migrate       # apply Alembic migrations
make logs          # tail all services
make health        # hit backend /health
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- Backend docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

## Default credentials

The first run seeds an admin user from env (`INIT_ADMIN_EMAIL`, `INIT_ADMIN_PASSWORD`):

```
QUANTGPT_ADMIN_EMAIL=admin@quantgpt.local
QUANTGPT_ADMIN_PASSWORD=ChangeMe123!
```

Change these in `.env` before any real deployment.

## Services

| Service | Port | Image |
|---|---|---|
| frontend | 3000 | node 22-alpine |
| backend | 8000 | python 3.12-slim |
| postgres | 5432 | postgres 16 |
| redis | 6379 | redis 7-alpine |

## Configuration

All runtime config is via environment variables (see `.env.example`). The backend uses Pydantic Settings (`app/config/settings.py`) with strict validation; the frontend reads `NEXT_PUBLIC_*` vars at build time.

## Development

```bash
make backend-shell    # enter backend container
make frontend-shell   # enter frontend container
make test             # run backend pytest
make lint            # ruff + biome
```

## License

Proprietary — QuantGPT. OpenAlgo is AGPL-3.0 and is consumed only as an external service.
