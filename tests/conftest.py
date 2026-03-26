"""SwarmChain test fixtures — in-memory SQLite for fast, isolated tests.

Strategy: Intercept create_async_engine at the SQLAlchemy level before
swarmchain.db.engine is imported, returning our test engine. Then replace
module-level objects via sys.modules for clean dependency override.
"""
import os
import sys
import asyncio

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

# ── 1. Force settings to SQLite BEFORE any swarmchain imports ─────
os.environ["SWARMCHAIN_DATABASE_URL"] = "sqlite+aiosqlite://"
os.environ["SWARMCHAIN_DATABASE_URL_SYNC"] = "sqlite://"
os.environ["SWARMCHAIN_REDIS_URL"] = "redis://localhost:6379/0"

# ── 2. Create the test engine (SQLite-compatible) ────────────────
test_engine = create_async_engine(
    "sqlite+aiosqlite://",
    echo=False,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestSessionFactory = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ── 3. Patch create_async_engine so engine.py uses our test engine ─
import sqlalchemy.ext.asyncio as _sqla_async

_original_cae = _sqla_async.create_async_engine


def _patched_cae(*args, **kwargs):
    """Always return the test engine, ignoring pool_size etc."""
    return test_engine


_sqla_async.create_async_engine = _patched_cae

# NOW import swarmchain — engine.py will use patched create_async_engine
from swarmchain.db.models import Base, Block, Attempt, Node, new_id  # noqa: E402
from swarmchain.db.engine import get_db  # noqa: E402

# Restore original
_sqla_async.create_async_engine = _original_cae

# Patch the session factory in the engine module via sys.modules
_engine_module = sys.modules["swarmchain.db.engine"]
_engine_module.async_session_factory = TestSessionFactory

# Also patch the controller and main module references that may
# have captured async_session_factory at import time
if "swarmchain.services.controller" in sys.modules:
    pass  # controller uses async_session_factory from engine module dynamically

from swarmchain.main import app  # noqa: E402
from httpx import AsyncClient, ASGITransport  # noqa: E402


# ── Fixtures ──────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def event_loop():
    """Use a single event loop for all session-scoped async fixtures."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def setup_tables():
    """Create all tables before each test, drop after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    """Yield a test database session."""
    async with TestSessionFactory() as session:
        yield session
        await session.rollback()


async def _override_get_db():
    """Dependency override that yields a test session."""
    async with TestSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@pytest_asyncio.fixture
async def test_client() -> AsyncClient:
    """HTTP test client with dependency overrides."""
    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


# ── Sample Data Fixtures ──────────────────────────────────────────

ARC_TASK_PAYLOAD = {
    "input_grid": [
        [0, 0, 0],
        [0, 2, 0],
        [0, 0, 0],
    ],
    "expected_output": [
        [1, 1, 1],
        [1, 2, 1],
        [1, 1, 1],
    ],
    "description": "Fill all zeros with blue (1)",
}


@pytest_asyncio.fixture
async def sample_node(db_session: AsyncSession) -> Node:
    """Create and return a registered test node."""
    node = Node(
        node_id="testnode001",
        node_type="gpu",
        hardware_class="rtx4090",
    )
    db_session.add(node)
    await db_session.commit()
    await db_session.refresh(node)
    return node


@pytest_asyncio.fixture
async def sample_block(db_session: AsyncSession) -> Block:
    """Create and return an open test block with an ARC task."""
    block = Block(
        block_id="testblock001",
        task_id="arc-001-fill-blue",
        domain="arc",
        reward_pool=100.0,
        max_attempts=500,
        time_limit_sec=3600,
        task_payload=ARC_TASK_PAYLOAD,
    )
    db_session.add(block)
    await db_session.commit()
    await db_session.refresh(block)
    return block


@pytest_asyncio.fixture
async def sample_attempt(db_session: AsyncSession, sample_block: Block, sample_node: Node) -> Attempt:
    """Create and return a scored test attempt (partial match)."""
    attempt = Attempt(
        attempt_id="testattempt01",
        block_id=sample_block.block_id,
        node_id=sample_node.node_id,
        method="test",
        strategy_family="brute_force",
        output_json={"grid": [[1, 1, 1], [1, 2, 1], [1, 1, 0]]},  # 8/9 correct
        score=8.0 / 9.0,
        valid=True,
        energy_cost=1.0,
        latency_ms=100,
    )
    db_session.add(attempt)
    await db_session.commit()
    await db_session.refresh(attempt)
    return attempt
