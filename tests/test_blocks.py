"""Tests for Block API endpoints."""
import pytest
import pytest_asyncio
from httpx import AsyncClient

from tests.conftest import ARC_TASK_PAYLOAD


@pytest.mark.asyncio
class TestCreateBlock:
    """POST /blocks/open creates a new reasoning block."""

    async def test_open_block_with_payload(self, test_client: AsyncClient):
        resp = await test_client.post("/blocks/open", json={
            "task_id": "test-task-001",
            "domain": "arc",
            "reward_pool": 200.0,
            "max_attempts": 100,
            "time_limit_sec": 1800,
            "task_payload": ARC_TASK_PAYLOAD,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["task_id"] == "test-task-001"
        assert data["domain"] == "arc"
        assert data["status"] == "open"
        assert data["reward_pool"] == 200.0
        assert data["max_attempts"] == 100
        assert data["time_limit_sec"] == 1800
        assert data["attempt_count"] == 0
        assert data["block_id"] is not None
        assert data["task_payload"]["expected_output"] == ARC_TASK_PAYLOAD["expected_output"]

    async def test_open_block_defaults(self, test_client: AsyncClient):
        resp = await test_client.post("/blocks/open", json={
            "task_id": "test-task-002",
            "task_payload": ARC_TASK_PAYLOAD,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["domain"] == "arc"
        assert data["reward_pool"] == 100.0
        assert data["max_attempts"] == 500
        assert data["time_limit_sec"] == 3600

    async def test_open_block_returns_start_time(self, test_client: AsyncClient):
        resp = await test_client.post("/blocks/open", json={
            "task_id": "test-task-003",
            "task_payload": ARC_TASK_PAYLOAD,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["start_time"] is not None
        assert data["end_time"] is None


@pytest.mark.asyncio
class TestListBlocks:
    """GET /blocks lists blocks with filters."""

    async def test_list_empty(self, test_client: AsyncClient):
        resp = await test_client.get("/blocks")
        assert resp.status_code == 200
        data = resp.json()
        assert data["blocks"] == []
        assert data["total"] == 0

    async def test_list_after_create(self, test_client: AsyncClient):
        # Create two blocks
        await test_client.post("/blocks/open", json={
            "task_id": "list-test-1",
            "task_payload": ARC_TASK_PAYLOAD,
        })
        await test_client.post("/blocks/open", json={
            "task_id": "list-test-2",
            "task_payload": ARC_TASK_PAYLOAD,
        })

        resp = await test_client.get("/blocks")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["blocks"]) == 2

    async def test_list_filter_by_status(self, test_client: AsyncClient):
        await test_client.post("/blocks/open", json={
            "task_id": "filter-test-1",
            "task_payload": ARC_TASK_PAYLOAD,
        })

        resp = await test_client.get("/blocks", params={"status": "open"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        for block in data["blocks"]:
            assert block["status"] == "open"

        resp = await test_client.get("/blocks", params={"status": "solved"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0

    async def test_list_filter_by_domain(self, test_client: AsyncClient):
        await test_client.post("/blocks/open", json={
            "task_id": "domain-test",
            "domain": "arc",
            "task_payload": ARC_TASK_PAYLOAD,
        })

        resp = await test_client.get("/blocks", params={"domain": "arc"})
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

        resp = await test_client.get("/blocks", params={"domain": "cre"})
        assert resp.status_code == 200
        assert resp.json()["total"] == 0


@pytest.mark.asyncio
class TestGetBlock:
    """GET /blocks/{id} returns a single block."""

    async def test_get_existing_block(self, test_client: AsyncClient):
        # Create a block first
        create_resp = await test_client.post("/blocks/open", json={
            "task_id": "get-test-1",
            "task_payload": ARC_TASK_PAYLOAD,
        })
        block_id = create_resp.json()["block_id"]

        resp = await test_client.get(f"/blocks/{block_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["block_id"] == block_id
        assert data["task_id"] == "get-test-1"

    async def test_get_nonexistent_block(self, test_client: AsyncClient):
        resp = await test_client.get("/blocks/nonexistent999")
        assert resp.status_code == 404
