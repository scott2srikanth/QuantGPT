"""FastAPI application entrypoint."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.api.v1.agents import router as agents_router
from app.api.v1.auth import router as auth_router
from app.api.v1.health import router as health_router
from app.api.v1.integration import router as integration_router
from app.api.v1.ml import router as ml_router
from app.api.v1.risk import router as risk_router
from app.api.v1.strategies import marketplace_router as strategies_marketplace_router
from app.api.v1.strategies import plugins_router as strategies_plugins_router
from app.api.v1.strategies import router as strategies_router
from app.api.v1.users import router as users_router
from app.config.settings import get_settings
from app.core.lifespan import lifespan
from app.observability.metrics import metrics_response
from app.observability.middleware import ProductionMiddleware
from app.observability.tracing import configure_tracing

_s = get_settings()

app = FastAPI(
    title="QuantGPT",
    description="AI-assisted algorithmic trading intelligence layer. Integrates with OpenAlgo via a dedicated Integration Layer.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_s.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=_s.trusted_hosts_list if _s.is_production else ["*"])
app.add_middleware(ProductionMiddleware)
configure_tracing(app)

api = "/api/v1"
app.include_router(auth_router, prefix=api)
app.include_router(users_router, prefix=api)
app.include_router(health_router, prefix=api)
app.include_router(integration_router, prefix=api)
app.include_router(agents_router, prefix=api)
app.include_router(strategies_router, prefix=api)
app.include_router(strategies_marketplace_router, prefix=api)
app.include_router(strategies_plugins_router, prefix=api)
app.include_router(ml_router, prefix=api)
app.include_router(risk_router, prefix=api)


@app.get("/", tags=["root"])
def root():
    return {"name": "QuantGPT", "version": "0.1.0", "docs": "/docs"}


@app.get("/metrics", include_in_schema=False)
def metrics():
    """Prometheus scrape endpoint; expose it only through a private monitoring network."""
    return metrics_response()
