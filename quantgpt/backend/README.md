# QuantGPT backend

FastAPI service providing auth, role management, health, and the OpenAlgo Integration Layer.

## Run

```bash
docker compose up -d backend
docker compose exec backend alembic upgrade head
```

Docs at http://localhost:8000/docs
