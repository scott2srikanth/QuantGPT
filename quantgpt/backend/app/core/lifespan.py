from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from app.auth.seeding import seed_admin_user
from app.logging.config import get_logger, setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    setup_logging()
    log = get_logger("app.lifespan")
    log.info("startup.begin")
    try:
        seed_admin_user()
    except Exception:
        log.exception("startup.admin_seed_failed")

    # Start the agent scheduler
    try:
        from app.core.container import get_container

        container = get_container()
        container.scheduler.start()
        log.info("startup.scheduler_started")
    except Exception:
        log.exception("startup.scheduler_failed")

    log.info("startup.complete")
    yield

    # Stop the scheduler on shutdown
    try:
        from app.core.container import get_container

        get_container().scheduler.stop()
    except Exception:
        log.exception("shutdown.scheduler_stop_failed")
    log.info("shutdown.complete")
