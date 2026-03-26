"""SwarmChain — Distributed Reasoning Ledger.

Search becomes data. Elimination becomes integrity. Finality creates value.
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from swarmchain.config import get_settings
from swarmchain.api import api_router
from swarmchain.services.controller import BlockController
from swarmchain.db.engine import engine
from swarmchain.db.models import Base

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("swarmchain")

controller = BlockController()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create tables, launch controller loop. Shutdown: stop loop."""
    # Create tables (dev mode — use Alembic migrations in prod)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables ensured")

    # Start controller background loop
    loop_task = asyncio.create_task(controller.run_loop())
    logger.info("Controller loop started")

    yield

    controller.stop()
    loop_task.cancel()
    logger.info("Controller loop stopped")

    await engine.dispose()


settings = get_settings()

app = FastAPI(
    title="SwarmChain",
    description="Distributed Reasoning Ledger — a contribution-aware search system",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/")
async def root():
    return {
        "service": "SwarmChain",
        "version": "0.1.0",
        "tagline": "Search becomes data. Elimination becomes integrity. Finality creates value.",
    }
