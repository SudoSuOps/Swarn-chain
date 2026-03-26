"""Integration test — full block lifecycle from registration to finality.

1. Register nodes
2. Open a block with ARC task
3. Submit multiple attempts (some bad, some good, one perfect)
4. Trigger finalization
5. Verify block is solved
6. Verify rewards are distributed
7. Verify artifacts are generated
"""
import pytest
from httpx import AsyncClient

from tests.conftest import ARC_TASK_PAYLOAD


@pytest.mark.asyncio
class TestFullBlockLifecycle:
    """End-to-end: nodes register, submit attempts, block solves, rewards flow."""

    async def test_full_flow(self, test_client: AsyncClient):
        client = test_client

        # ── 1. Register nodes ────────────────────────────────
        node_ids = []
        for i, (ntype, hw) in enumerate([
            ("gpu", "rtx4090"),
            ("gpu", "a100"),
            ("cpu", "xeon"),
        ]):
            resp = await client.post("/nodes/register", json={
                "node_id": f"integ_node_{i}",
                "node_type": ntype,
                "hardware_class": hw,
            })
            assert resp.status_code == 200
            node_ids.append(resp.json()["node_id"])

        # Verify nodes registered
        resp = await client.get("/nodes")
        assert resp.status_code == 200
        registered = {n["node_id"] for n in resp.json()}
        for nid in node_ids:
            assert nid in registered

        # ── 2. Open a block with ARC task ────────────────────
        resp = await client.post("/blocks/open", json={
            "task_id": "arc-integration-test",
            "domain": "arc",
            "reward_pool": 100.0,
            "max_attempts": 50,
            "time_limit_sec": 3600,
            "task_payload": ARC_TASK_PAYLOAD,
        })
        assert resp.status_code == 200
        block_id = resp.json()["block_id"]
        assert resp.json()["status"] == "open"

        # ── 3. Submit multiple attempts ──────────────────────

        # Attempt 1: node_0 submits garbage (wrong dims) -> score 0.0
        resp = await client.post("/attempts", json={
            "block_id": block_id,
            "node_id": node_ids[0],
            "method": "random",
            "strategy_family": "brute_force",
            "output_json": {"grid": [[9, 9], [9, 9]]},
            "energy_cost": 1.0,
            "latency_ms": 50,
        })
        assert resp.status_code == 200
        att1_id = resp.json()["attempt_id"]
        assert resp.json()["score"] == 0.0
        assert resp.json()["valid"] is False

        # Attempt 2: node_0 submits partial (6/9 correct)
        resp = await client.post("/attempts", json={
            "block_id": block_id,
            "node_id": node_ids[0],
            "method": "heuristic",
            "strategy_family": "gradient",
            "output_json": {
                "grid": [
                    [1, 1, 0],
                    [1, 2, 0],
                    [1, 1, 0],
                ]
            },
            "energy_cost": 1.5,
            "latency_ms": 100,
        })
        assert resp.status_code == 200
        att2_id = resp.json()["attempt_id"]
        att2_score = resp.json()["score"]
        assert att2_score > 0.0
        assert att2_score < 1.0

        # Attempt 3: node_2 submits another partial, derived from attempt 2
        resp = await client.post("/attempts", json={
            "block_id": block_id,
            "node_id": node_ids[2],
            "parent_attempt_id": att2_id,
            "method": "refinement",
            "strategy_family": "gradient",
            "output_json": {
                "grid": [
                    [1, 1, 1],
                    [1, 2, 1],
                    [1, 1, 0],  # 8/9 correct
                ]
            },
            "energy_cost": 1.0,
            "latency_ms": 80,
        })
        assert resp.status_code == 200
        att3_id = resp.json()["attempt_id"]
        att3_score = resp.json()["score"]
        assert att3_score > att2_score  # improvement

        # Attempt 4: node_1 submits the PERFECT answer, derived from attempt 3
        resp = await client.post("/attempts", json={
            "block_id": block_id,
            "node_id": node_ids[1],
            "parent_attempt_id": att3_id,
            "method": "exact_solve",
            "strategy_family": "solver",
            "output_json": {
                "grid": [
                    [1, 1, 1],
                    [1, 2, 1],
                    [1, 1, 1],
                ]
            },
            "energy_cost": 2.0,
            "latency_ms": 200,
        })
        assert resp.status_code == 200
        att4_id = resp.json()["attempt_id"]
        assert resp.json()["score"] == 1.0
        assert resp.json()["valid"] is True

        # Attempt 5: node_2 submits an independent explorer attempt
        resp = await client.post("/attempts", json={
            "block_id": block_id,
            "node_id": node_ids[2],
            "method": "creative_search",
            "strategy_family": "explorer",
            "output_json": {
                "grid": [
                    [1, 1, 1],
                    [1, 2, 1],
                    [0, 0, 0],  # 6/9 correct
                ]
            },
            "energy_cost": 0.5,
            "latency_ms": 30,
        })
        assert resp.status_code == 200
        att5_id = resp.json()["attempt_id"]

        # Verify block has correct attempt count
        resp = await client.get(f"/blocks/{block_id}")
        assert resp.json()["attempt_count"] == 5

        # ── 4. Trigger finalization ──────────────────────────
        resp = await client.post(f"/blocks/{block_id}/finalize", json={"force": False})
        assert resp.status_code == 200

        # ── 5. Verify block is solved ────────────────────────
        resp = await client.get(f"/blocks/{block_id}")
        assert resp.status_code == 200
        block_data = resp.json()
        assert block_data["status"] == "solved"
        assert block_data["winning_attempt_id"] == att4_id
        assert block_data["winning_node_id"] == node_ids[1]
        assert block_data["final_score"] == 1.0
        assert block_data["end_time"] is not None
        assert block_data["elimination_summary"] is not None
        assert block_data["elimination_summary"]["total_attempts"] == 5

        # ── 6. Verify rewards are distributed ────────────────
        resp = await client.get(f"/blocks/{block_id}/rewards")
        assert resp.status_code == 200
        reward_data = resp.json()
        assert reward_data["total_pool"] == 100.0
        assert reward_data["solver_pool"] == 40.0
        assert reward_data["lineage_pool"] == 30.0
        assert reward_data["exploration_pool"] == 20.0
        assert reward_data["efficiency_pool"] == 10.0
        assert len(reward_data["rewards"]) > 0

        # Check solver reward goes to node_1
        solver_rewards = [r for r in reward_data["rewards"] if r["reward_type"] == "solver"]
        assert len(solver_rewards) == 1
        assert solver_rewards[0]["node_id"] == node_ids[1]
        assert solver_rewards[0]["reward_amount"] == pytest.approx(40.0, rel=1e-3)

        # Check lineage rewards exist (ancestors of winning path)
        lineage_rewards = [r for r in reward_data["rewards"] if r["reward_type"] == "lineage"]
        assert len(lineage_rewards) > 0

        # Check exploration rewards exist
        exploration_rewards = [r for r in reward_data["rewards"] if r["reward_type"] == "exploration"]
        assert len(exploration_rewards) > 0

        # Check efficiency rewards exist
        efficiency_rewards = [r for r in reward_data["rewards"] if r["reward_type"] == "efficiency"]
        assert len(efficiency_rewards) > 0

        # Verify total distributed does not exceed pool
        total_distributed = sum(r["reward_amount"] for r in reward_data["rewards"])
        assert total_distributed <= 100.0 + 0.01

        # ── 7. Verify artifacts are generated ────────────────
        resp = await client.get(f"/blocks/{block_id}/artifacts")
        assert resp.status_code == 200
        artifacts = resp.json()
        assert len(artifacts) >= 1

        sealed = artifacts[0]
        assert sealed["artifact_type"] == "sealed_block"
        assert sealed["artifact_json"]["block_id"] == block_id
        assert sealed["artifact_json"]["status"] == "solved"
        assert sealed["artifact_json"]["final_score"] == 1.0
        assert sealed["artifact_json"]["winning_attempt_id"] == att4_id
        assert len(sealed["artifact_json"]["winning_lineage"]) >= 1
        assert len(sealed["artifact_json"]["contributing_nodes"]) >= 2
        assert sealed["artifact_json"]["elimination_summary"]["total_attempts"] == 5

        # Verify the winning lineage traces the path
        lineage_path = sealed["artifact_json"]["winning_lineage"]
        lineage_ids = [step["attempt_id"] for step in lineage_path]
        # att2 -> att3 -> att4 should be in the lineage
        assert att4_id in lineage_ids

    async def test_block_cannot_accept_attempts_after_solved(self, test_client: AsyncClient):
        """Once a block is solved, new attempts should be rejected."""
        client = test_client

        # Setup: register node, open block, submit perfect answer, finalize
        resp = await client.post("/nodes/register", json={
            "node_id": "closed_test_node",
            "node_type": "gpu",
            "hardware_class": "rtx4090",
        })
        node_id = resp.json()["node_id"]

        resp = await client.post("/blocks/open", json={
            "task_id": "closed-test",
            "task_payload": ARC_TASK_PAYLOAD,
        })
        block_id = resp.json()["block_id"]

        # Submit perfect answer
        await client.post("/attempts", json={
            "block_id": block_id,
            "node_id": node_id,
            "output_json": {"grid": [[1, 1, 1], [1, 2, 1], [1, 1, 1]]},
        })

        # Finalize
        await client.post(f"/blocks/{block_id}/finalize", json={"force": False})

        # Verify block is solved
        resp = await client.get(f"/blocks/{block_id}")
        assert resp.json()["status"] == "solved"

        # Try to submit another attempt — should fail
        resp = await client.post("/attempts", json={
            "block_id": block_id,
            "node_id": node_id,
            "output_json": {"grid": [[1, 1, 1], [1, 2, 1], [1, 1, 1]]},
        })
        assert resp.status_code == 400

    async def test_node_stats_updated_after_flow(self, test_client: AsyncClient):
        """Node stats reflect contributions after a full flow."""
        client = test_client

        resp = await client.post("/nodes/register", json={
            "node_id": "stats_node",
            "node_type": "gpu",
            "hardware_class": "rtx4090",
        })
        node_id = resp.json()["node_id"]

        resp = await client.post("/blocks/open", json={
            "task_id": "stats-test",
            "task_payload": ARC_TASK_PAYLOAD,
        })
        block_id = resp.json()["block_id"]

        # Submit 3 attempts
        for grid in [
            [[0, 0, 0], [0, 0, 0], [0, 0, 0]],
            [[1, 1, 0], [1, 2, 0], [1, 1, 0]],
            [[1, 1, 1], [1, 2, 1], [1, 1, 1]],
        ]:
            await client.post("/attempts", json={
                "block_id": block_id,
                "node_id": node_id,
                "output_json": {"grid": grid},
                "energy_cost": 1.0,
            })

        # Check node stats
        resp = await client.get(f"/nodes/{node_id}")
        assert resp.status_code == 200
        node_data = resp.json()
        assert node_data["total_attempts"] == 3
        assert node_data["total_energy_used"] == 3.0
