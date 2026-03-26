"""Tests for Attempt API endpoints — submit, score, inspect, lineage."""
import pytest
import pytest_asyncio
from httpx import AsyncClient

from tests.conftest import ARC_TASK_PAYLOAD


async def _create_block(client: AsyncClient) -> str:
    """Helper: create a block and return its block_id."""
    resp = await client.post("/blocks/open", json={
        "task_id": "attempt-test-task",
        "task_payload": ARC_TASK_PAYLOAD,
    })
    return resp.json()["block_id"]


async def _register_node(client: AsyncClient, node_id: str = "atnode001") -> str:
    """Helper: register a node and return its node_id."""
    resp = await client.post("/nodes/register", json={
        "node_id": node_id,
        "node_type": "gpu",
        "hardware_class": "rtx4090",
    })
    return resp.json()["node_id"]


@pytest.mark.asyncio
class TestSubmitAttempt:
    """POST /attempts scores and stores an attempt."""

    async def test_submit_correct_attempt(self, test_client: AsyncClient):
        block_id = await _create_block(test_client)
        node_id = await _register_node(test_client)

        resp = await test_client.post("/attempts", json={
            "block_id": block_id,
            "node_id": node_id,
            "method": "brute_force",
            "strategy_family": "exact",
            "output_json": {
                "grid": [
                    [1, 1, 1],
                    [1, 2, 1],
                    [1, 1, 1],
                ]
            },
            "energy_cost": 2.5,
            "latency_ms": 150,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["score"] == 1.0
        assert data["valid"] is True
        assert data["block_id"] == block_id
        assert data["node_id"] == node_id
        assert data["method"] == "brute_force"
        assert data["energy_cost"] == 2.5
        assert data["attempt_id"] is not None

    async def test_submit_partial_attempt(self, test_client: AsyncClient):
        block_id = await _create_block(test_client)
        node_id = await _register_node(test_client)

        resp = await test_client.post("/attempts", json={
            "block_id": block_id,
            "node_id": node_id,
            "output_json": {
                "grid": [
                    [1, 1, 1],
                    [1, 2, 1],
                    [1, 1, 0],  # 1 wrong cell
                ]
            },
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["score"] == pytest.approx(8.0 / 9.0, rel=1e-3)
        assert data["valid"] is True

    async def test_submit_bad_grid(self, test_client: AsyncClient):
        block_id = await _create_block(test_client)
        node_id = await _register_node(test_client)

        resp = await test_client.post("/attempts", json={
            "block_id": block_id,
            "node_id": node_id,
            "output_json": {"grid": [[0, 0], [0, 0]]},  # wrong dimensions
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["score"] == 0.0
        assert data["valid"] is False

    async def test_submit_no_grid(self, test_client: AsyncClient):
        block_id = await _create_block(test_client)
        node_id = await _register_node(test_client)

        resp = await test_client.post("/attempts", json={
            "block_id": block_id,
            "node_id": node_id,
            "output_json": {"answer": "wrong format"},
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["score"] == 0.0
        assert data["valid"] is False

    async def test_submit_to_nonexistent_block(self, test_client: AsyncClient):
        node_id = await _register_node(test_client)
        resp = await test_client.post("/attempts", json={
            "block_id": "ghost_block",
            "node_id": node_id,
            "output_json": {"grid": [[1]]},
        })
        assert resp.status_code == 404

    async def test_submit_with_nonexistent_node(self, test_client: AsyncClient):
        block_id = await _create_block(test_client)
        resp = await test_client.post("/attempts", json={
            "block_id": block_id,
            "node_id": "ghost_node",
            "output_json": {"grid": [[1]]},
        })
        assert resp.status_code == 404

    async def test_submit_increments_block_counters(self, test_client: AsyncClient):
        block_id = await _create_block(test_client)
        node_id = await _register_node(test_client)

        await test_client.post("/attempts", json={
            "block_id": block_id,
            "node_id": node_id,
            "output_json": {"grid": [[1, 1, 1], [1, 2, 1], [1, 1, 1]]},
            "energy_cost": 3.0,
        })

        resp = await test_client.get(f"/blocks/{block_id}")
        data = resp.json()
        assert data["attempt_count"] == 1
        assert data["total_energy"] == 3.0


@pytest.mark.asyncio
class TestGetAttempt:
    """GET /attempts/{id} returns an attempt."""

    async def test_get_existing_attempt(self, test_client: AsyncClient):
        block_id = await _create_block(test_client)
        node_id = await _register_node(test_client)

        create_resp = await test_client.post("/attempts", json={
            "block_id": block_id,
            "node_id": node_id,
            "output_json": {"grid": [[1, 1, 1], [1, 2, 1], [1, 1, 1]]},
        })
        attempt_id = create_resp.json()["attempt_id"]

        resp = await test_client.get(f"/attempts/{attempt_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["attempt_id"] == attempt_id
        assert data["score"] == 1.0

    async def test_get_nonexistent_attempt(self, test_client: AsyncClient):
        resp = await test_client.get("/attempts/nonexistent999")
        assert resp.status_code == 404


@pytest.mark.asyncio
class TestLineageEdgeCreation:
    """Lineage edges are recorded when parent_attempt_id is provided."""

    async def test_lineage_edge_created(self, test_client: AsyncClient):
        block_id = await _create_block(test_client)
        node_id = await _register_node(test_client)

        # Submit parent attempt
        parent_resp = await test_client.post("/attempts", json={
            "block_id": block_id,
            "node_id": node_id,
            "method": "random_guess",
            "output_json": {
                "grid": [
                    [0, 0, 0],
                    [0, 2, 0],
                    [0, 0, 0],
                ]
            },
        })
        parent_id = parent_resp.json()["attempt_id"]
        parent_score = parent_resp.json()["score"]

        # Submit child attempt referencing parent
        child_resp = await test_client.post("/attempts", json={
            "block_id": block_id,
            "node_id": node_id,
            "parent_attempt_id": parent_id,
            "method": "refined_guess",
            "output_json": {
                "grid": [
                    [1, 1, 1],
                    [1, 2, 1],
                    [1, 1, 1],
                ]
            },
        })
        assert child_resp.status_code == 200
        child_data = child_resp.json()
        assert child_data["parent_attempt_id"] == parent_id

        # Verify lineage graph has the edge
        lineage_resp = await test_client.get(f"/attempts/block/{block_id}/lineage")
        assert lineage_resp.status_code == 200
        edges = lineage_resp.json()["edges"]
        assert len(edges) >= 1
        edge = edges[0]
        assert edge["parent"] == parent_id
        assert edge["child"] == child_data["attempt_id"]
        # Delta should be positive (child scored better)
        assert edge["delta_score"] > 0

    async def test_no_lineage_without_parent(self, test_client: AsyncClient):
        block_id = await _create_block(test_client)
        node_id = await _register_node(test_client)

        await test_client.post("/attempts", json={
            "block_id": block_id,
            "node_id": node_id,
            "output_json": {"grid": [[1, 1, 1], [1, 2, 1], [1, 1, 1]]},
        })

        lineage_resp = await test_client.get(f"/attempts/block/{block_id}/lineage")
        assert lineage_resp.status_code == 200
        assert lineage_resp.json()["edges"] == []
