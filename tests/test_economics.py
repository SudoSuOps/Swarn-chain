"""Tests for the economic layer — reputation, anti-spam, diminishing returns, dataset sales."""
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from swarmchain.db.models import (
    Node, Block, Attempt, Reward, DatasetSale, BlockArtifact, new_id,
)
from swarmchain.services.reputation import ReputationService
from swarmchain.services.economics import EconomicsEngine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _make_node(
    db: AsyncSession,
    node_id: str,
    reputation: float = 1.0,
    **kwargs,
) -> Node:
    """Create a node with optional overrides."""
    node = Node(
        node_id=node_id,
        node_type=kwargs.pop("node_type", "gpu"),
        hardware_class=kwargs.pop("hardware_class", "rtx4090"),
        reputation_score=reputation,
        active=kwargs.pop("active", True),
        total_energy_used=kwargs.pop("total_energy_used", 0.0),
        total_attempts=kwargs.pop("total_attempts", 0),
        total_solves=kwargs.pop("total_solves", 0),
        total_rewards=kwargs.pop("total_rewards", 0.0),
    )
    db.add(node)
    await db.flush()
    return node


async def _make_block(
    db: AsyncSession,
    block_id: str,
    status: str = "solved",
    reward_pool: float = 100.0,
    **kwargs,
) -> Block:
    block = Block(
        block_id=block_id,
        task_id=kwargs.pop("task_id", "arc-test"),
        domain=kwargs.pop("domain", "arc"),
        status=status,
        reward_pool=reward_pool,
        max_attempts=500,
        time_limit_sec=3600,
        task_payload=kwargs.pop("task_payload", {"expected_output": [[1]]}),
        attempt_count=kwargs.pop("attempt_count", 0),
        total_energy=kwargs.pop("total_energy", 0.0),
        winning_attempt_id=kwargs.pop("winning_attempt_id", None),
        winning_node_id=kwargs.pop("winning_node_id", None),
        final_score=kwargs.pop("final_score", None),
    )
    db.add(block)
    await db.flush()
    return block


async def _make_attempt(
    db: AsyncSession,
    attempt_id: str,
    block_id: str,
    node_id: str,
    score: float = 0.5,
    **kwargs,
) -> Attempt:
    attempt = Attempt(
        attempt_id=attempt_id,
        block_id=block_id,
        node_id=node_id,
        method=kwargs.pop("method", "test"),
        strategy_family=kwargs.pop("strategy_family", "brute_force"),
        output_json=kwargs.pop("output_json", {"grid": [[score]]}),
        score=score,
        valid=kwargs.pop("valid", True),
        energy_cost=kwargs.pop("energy_cost", 1.0),
        latency_ms=kwargs.pop("latency_ms", 100),
        promoted=kwargs.pop("promoted", False),
    )
    db.add(attempt)
    await db.flush()
    return attempt


async def _make_reward(
    db: AsyncSession,
    block_id: str,
    node_id: str,
    reward_type: str = "solver",
    reward_amount: float = 10.0,
    score_basis: float = 1.0,
) -> Reward:
    reward = Reward(
        block_id=block_id,
        node_id=node_id,
        reward_type=reward_type,
        reward_amount=reward_amount,
        score_basis=score_basis,
    )
    db.add(reward)
    await db.flush()
    return reward


async def _setup_finalized_block_with_rewards(
    db: AsyncSession,
    block_id: str = "econ_block_01",
) -> tuple[Block, list[Node], list[Reward]]:
    """Create a finalized block with three nodes and proportional rewards.

    node_a: 60 reward (solver + lineage)
    node_b: 30 reward (exploration)
    node_c: 10 reward (efficiency)
    Total: 100
    """
    node_a = await _make_node(db, "econ_node_a", reputation=1.2)
    node_b = await _make_node(db, "econ_node_b", reputation=1.0)
    node_c = await _make_node(db, "econ_node_c", reputation=0.8)

    block = await _make_block(
        db,
        block_id,
        status="solved",
        reward_pool=100.0,
        winning_attempt_id="econ_att_a1",
        winning_node_id="econ_node_a",
        final_score=1.0,
        attempt_count=6,
        total_energy=10.0,
    )

    # Attempts — varied strategies/outputs, all above spam threshold
    await _make_attempt(db, "econ_att_a1", block_id, "econ_node_a", score=1.0,
                        strategy_family="solver", output_json={"grid": [[1, 1]]})
    await _make_attempt(db, "econ_att_a2", block_id, "econ_node_a", score=0.7,
                        strategy_family="gradient", output_json={"grid": [[1, 0]]})
    await _make_attempt(db, "econ_att_b1", block_id, "econ_node_b", score=0.5,
                        strategy_family="explorer", output_json={"grid": [[0, 1]]})
    await _make_attempt(db, "econ_att_b2", block_id, "econ_node_b", score=0.4,
                        strategy_family="heuristic", output_json={"grid": [[0, 0]]})
    await _make_attempt(db, "econ_att_c1", block_id, "econ_node_c", score=0.3,
                        strategy_family="random", output_json={"grid": [[1, 0]]})
    await _make_attempt(db, "econ_att_c2", block_id, "econ_node_c", score=0.2,
                        strategy_family="brute_force", output_json={"grid": [[0, 0]]})

    # Rewards from original block solve
    r_a = await _make_reward(db, block_id, "econ_node_a", "solver", 60.0, 1.0)
    r_b = await _make_reward(db, block_id, "econ_node_b", "exploration", 30.0, 0.5)
    r_c = await _make_reward(db, block_id, "econ_node_c", "efficiency", 10.0, 0.3)

    await db.commit()
    return block, [node_a, node_b, node_c], [r_a, r_b, r_c]


# ===========================================================================
# TestReputationService
# ===========================================================================


@pytest.mark.asyncio
class TestReputationService:
    """Reputation changes after block participation."""

    async def test_solve_boosts_reputation(self, db_session: AsyncSession):
        """A node that achieves score=1.0 (valid=True) gets a reputation boost."""
        node = await _make_node(db_session, "rep_solver", reputation=1.0)
        block = await _make_block(db_session, "rep_block_solve", status="solved")
        await _make_attempt(
            db_session, "rep_att_solve", block.block_id, node.node_id,
            score=1.0, valid=True,
        )
        await db_session.commit()

        svc = ReputationService()
        updates = await svc.update_after_block(db_session, block.block_id)
        await db_session.commit()

        assert updates[node.node_id] > 1.0, "Solving should raise reputation above starting 1.0"

    async def test_spam_penalizes_reputation(self, db_session: AsyncSession):
        """Many below-threshold attempts should lower reputation."""
        node = await _make_node(db_session, "rep_spammer", reputation=1.0)
        block = await _make_block(db_session, "rep_block_spam", status="exhausted")

        # 10 attempts all with score below spam_threshold (0.02)
        for i in range(10):
            await _make_attempt(
                db_session, f"rep_spam_{i:03d}", block.block_id, node.node_id,
                score=0.001, valid=False,
                output_json={"grid": [[i]]},  # different outputs to avoid duplicate penalty overlap
            )
        await db_session.commit()

        svc = ReputationService()
        updates = await svc.update_after_block(db_session, block.block_id)
        await db_session.commit()

        assert updates[node.node_id] < 1.0, "Spam attempts should decrease reputation"

    async def test_duplicate_pattern_penalty(self, db_session: AsyncSession):
        """Repeated identical scores (>3 repeats) trigger duplicate penalty."""
        node = await _make_node(db_session, "rep_dupe", reputation=1.0)
        block = await _make_block(db_session, "rep_block_dupe", status="exhausted")

        # 8 attempts with the exact same score = 0.5 (above spam threshold)
        for i in range(8):
            await _make_attempt(
                db_session, f"rep_dupe_{i:03d}", block.block_id, node.node_id,
                score=0.5, valid=True,
                output_json={"grid": [[i]]},
            )
        await db_session.commit()

        svc = ReputationService()
        updates = await svc.update_after_block(db_session, block.block_id)
        await db_session.commit()

        # Duplicate penalty: spam_penalty * 0.5 * (8 - 3) = 0.1 * 0.5 * 5 = 0.25
        assert updates[node.node_id] < 1.0, "Duplicate score pattern should penalize reputation"

    async def test_reputation_clamped(self, db_session: AsyncSession):
        """Reputation stays within [0.0, 2.0] regardless of extreme inputs."""
        # Test upper bound: node already at 1.95, solve a block
        node_high = await _make_node(db_session, "rep_high", reputation=1.95)
        block_high = await _make_block(db_session, "rep_block_high", status="solved")
        # Multiple solves to push reputation
        for i in range(5):
            await _make_attempt(
                db_session, f"rep_high_{i:03d}", block_high.block_id, node_high.node_id,
                score=1.0, valid=True, promoted=True,
                output_json={"grid": [[10 + i]]},
            )
        await db_session.commit()

        svc = ReputationService()
        updates = await svc.update_after_block(db_session, block_high.block_id)
        await db_session.commit()
        assert updates[node_high.node_id] <= 2.0, "Reputation must not exceed 2.0"

        # Test lower bound: node at 0.05, heavy spam
        node_low = await _make_node(db_session, "rep_low", reputation=0.05)
        block_low = await _make_block(db_session, "rep_block_low", status="exhausted")
        for i in range(20):
            await _make_attempt(
                db_session, f"rep_low_{i:03d}", block_low.block_id, node_low.node_id,
                score=0.001, valid=False,
                output_json={"grid": [[i]]},
            )
        await db_session.commit()

        updates2 = await svc.update_after_block(db_session, block_low.block_id)
        await db_session.commit()
        assert updates2[node_low.node_id] >= 0.0, "Reputation must not go below 0.0"

    async def test_leaderboard_ordered_by_reputation(self, db_session: AsyncSession):
        """get_leaderboard returns nodes sorted by reputation descending."""
        await _make_node(db_session, "lb_low", reputation=0.5)
        await _make_node(db_session, "lb_mid", reputation=1.2)
        await _make_node(db_session, "lb_high", reputation=1.8)
        await db_session.commit()

        svc = ReputationService()
        board = await svc.get_leaderboard(db_session, limit=10)

        assert len(board) == 3
        assert board[0]["node_id"] == "lb_high"
        assert board[1]["node_id"] == "lb_mid"
        assert board[2]["node_id"] == "lb_low"
        # Confirm descending order
        reps = [entry["reputation_score"] for entry in board]
        assert reps == sorted(reps, reverse=True)


# ===========================================================================
# TestAntiSpam
# ===========================================================================


@pytest.mark.asyncio
class TestAntiSpam:
    """Anti-spam detection and payout penalty."""

    async def test_spam_attempts_detected(self, db_session: AsyncSession):
        """detect_spam_attempts returns attempts below the spam threshold."""
        node = await _make_node(db_session, "spam_det_node")
        block = await _make_block(db_session, "spam_det_block")

        # 3 below threshold, 2 above
        await _make_attempt(db_session, "sd_01", block.block_id, node.node_id, score=0.001)
        await _make_attempt(db_session, "sd_02", block.block_id, node.node_id, score=0.005)
        await _make_attempt(db_session, "sd_03", block.block_id, node.node_id, score=0.01)
        await _make_attempt(db_session, "sd_04", block.block_id, node.node_id, score=0.5)
        await _make_attempt(db_session, "sd_05", block.block_id, node.node_id, score=0.8)
        await db_session.commit()

        spam = await ReputationService.detect_spam_attempts(db_session, block.block_id)
        # spam_score_threshold = 0.02 in config, so scores < 0.02 are spam
        spam_ids = {s["attempt_id"] for s in spam}
        assert "sd_01" in spam_ids
        assert "sd_02" in spam_ids
        assert "sd_03" in spam_ids
        assert "sd_04" not in spam_ids
        assert "sd_05" not in spam_ids

    async def test_spam_ratio_reduces_payout_multiplier(self, db_session: AsyncSession):
        """>50% spam ratio should apply the heavy spam_penalty_multiplier (0.1)."""
        node = await _make_node(db_session, "spam_heavy_node", reputation=1.0)
        block = await _make_block(db_session, "spam_heavy_block")

        # 8 spam, 2 good => spam_ratio = 0.8 > 0.5
        # Use varied strategies so strategy_monotony penalty doesn't compound
        strategies = ["s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8"]
        for i in range(8):
            await _make_attempt(
                db_session, f"sh_{i:03d}", block.block_id, node.node_id,
                score=0.001, output_json={"grid": [[i]]},
                strategy_family=strategies[i],
            )
        await _make_attempt(db_session, "sh_good_1", block.block_id, node.node_id,
                            score=0.5, strategy_family="s9")
        await _make_attempt(db_session, "sh_good_2", block.block_id, node.node_id,
                            score=0.8, strategy_family="s10")
        await db_session.commit()

        engine = EconomicsEngine()
        attempts_result = await db_session.execute(
            select(Attempt).where(Attempt.block_id == block.block_id)
        )
        all_attempts = list(attempts_result.scalars().all())
        nodes_map = {node.node_id: node}

        penalties = engine._compute_penalties(all_attempts, nodes_map)

        # spam_ratio = 0.8 > 0.5 => multiplier = spam_penalty_multiplier = 0.1
        assert penalties[node.node_id]["multiplier"] == pytest.approx(0.1, abs=0.01)

    async def test_partial_spam_moderate_penalty(self, db_session: AsyncSession):
        """20-50% spam ratio applies a moderate penalty (multiplier = 1 - ratio)."""
        node = await _make_node(db_session, "spam_mod_node", reputation=1.0)
        block = await _make_block(db_session, "spam_mod_block")

        # 3 spam, 7 good => spam_ratio = 0.3 (between 0.2 and 0.5)
        # Use varied strategies to isolate the spam penalty from strategy_monotony
        for i in range(3):
            await _make_attempt(
                db_session, f"sm_{i:03d}", block.block_id, node.node_id,
                score=0.001, output_json={"grid": [[i]]},
                strategy_family=f"spam_strat_{i}",
            )
        for i in range(7):
            await _make_attempt(
                db_session, f"sm_good_{i:03d}", block.block_id, node.node_id,
                score=0.5, output_json={"grid": [[100 + i]]},
                strategy_family=f"good_strat_{i}",
            )
        await db_session.commit()

        engine = EconomicsEngine()
        attempts_result = await db_session.execute(
            select(Attempt).where(Attempt.block_id == block.block_id)
        )
        all_attempts = list(attempts_result.scalars().all())
        nodes_map = {node.node_id: node}

        penalties = engine._compute_penalties(all_attempts, nodes_map)

        # spam_ratio = 0.3, between 0.2 and 0.5 => multiplier = 1.0 - 0.3 = 0.7
        assert penalties[node.node_id]["multiplier"] == pytest.approx(0.7, abs=0.05)


# ===========================================================================
# TestDiminishingReturns
# ===========================================================================


@pytest.mark.asyncio
class TestDiminishingReturns:
    """Diminishing returns for duplicate outputs and strategy monotony."""

    async def test_duplicate_outputs_decay(self, db_session: AsyncSession):
        """Same output submitted 5+ times should apply duplicate decay."""
        node = await _make_node(db_session, "dr_dupe_node", reputation=1.0)
        block = await _make_block(db_session, "dr_dupe_block")

        identical_output = {"grid": [[1, 1], [1, 1]]}
        # 6 identical outputs (>3 triggers decay)
        for i in range(6):
            await _make_attempt(
                db_session, f"drd_{i:03d}", block.block_id, node.node_id,
                score=0.5, output_json=identical_output,
                strategy_family=f"strat_{i}",  # diverse strategies to isolate duplicate test
            )
        await db_session.commit()

        engine = EconomicsEngine()
        attempts_result = await db_session.execute(
            select(Attempt).where(Attempt.block_id == block.block_id)
        )
        all_attempts = list(attempts_result.scalars().all())
        nodes_map = {node.node_id: node}

        penalties = engine._compute_penalties(all_attempts, nodes_map)

        # max_repeats=6 > 3, decay = 0.5^(6-3) = 0.125
        assert penalties[node.node_id]["multiplier"] < 0.5
        assert penalties[node.node_id]["duplicate_max"] == 6

    async def test_strategy_monotony_penalty(self, db_session: AsyncSession):
        """Using the same strategy for >80% of attempts (with >5 total) gets penalized."""
        node = await _make_node(db_session, "dr_mono_node", reputation=1.0)
        block = await _make_block(db_session, "dr_mono_block")

        # 9/10 = 90% same strategy, all unique outputs and above spam threshold
        for i in range(9):
            await _make_attempt(
                db_session, f"drm_{i:03d}", block.block_id, node.node_id,
                score=0.5, strategy_family="brute_force",
                output_json={"grid": [[i, i + 1]]},  # unique outputs
            )
        await _make_attempt(
            db_session, "drm_other", block.block_id, node.node_id,
            score=0.5, strategy_family="explorer",
            output_json={"grid": [[99, 99]]},
        )
        await db_session.commit()

        engine = EconomicsEngine()
        attempts_result = await db_session.execute(
            select(Attempt).where(Attempt.block_id == block.block_id)
        )
        all_attempts = list(attempts_result.scalars().all())
        nodes_map = {node.node_id: node}

        penalties = engine._compute_penalties(all_attempts, nodes_map)

        # 90% brute_force > 80% threshold => multiplier *= 0.8
        assert penalties[node.node_id]["multiplier"] == pytest.approx(0.8, abs=0.05)
        assert "strategy_monotony" in (penalties[node.node_id].get("reason") or "")


# ===========================================================================
# TestDatasetSale
# ===========================================================================


@pytest.mark.asyncio
class TestDatasetSale:
    """Dataset sale execution — distribution, fees, reputation gating, records."""

    async def test_sale_distributes_proportional_to_rewards(self, db_session: AsyncSession):
        """Payout shares match original reward proportions (before bonuses/penalties)."""
        block, nodes, rewards = await _setup_finalized_block_with_rewards(db_session)

        engine = EconomicsEngine()
        sale = await engine.execute_dataset_sale(
            db_session, block.block_id, "buyer_corp", 1000.0, platform_fee_pct=0.10,
        )
        await db_session.commit()

        payouts = sale.payout_summary["payouts"]
        payout_map = {p["node_id"]: p for p in payouts}

        # Original rewards: a=60, b=30, c=10 => total=100
        # Shares: a=0.6, b=0.3, c=0.1
        # Distributable = 1000 - 100 (10% fee) = 900
        # Base payouts before penalties: a=540, b=270, c=90
        assert payout_map["econ_node_a"]["original_share"] == pytest.approx(60.0)
        assert payout_map["econ_node_b"]["original_share"] == pytest.approx(30.0)
        assert payout_map["econ_node_c"]["original_share"] == pytest.approx(10.0)

        # Base payouts should be proportional to original share
        assert payout_map["econ_node_a"]["base_payout"] == pytest.approx(
            900.0 * 60 / 100, rel=0.01,
        )
        assert payout_map["econ_node_b"]["base_payout"] == pytest.approx(
            900.0 * 30 / 100, rel=0.01,
        )

    async def test_platform_fee_deducted(self, db_session: AsyncSession):
        """10% platform fee is deducted before distribution."""
        block, nodes, rewards = await _setup_finalized_block_with_rewards(db_session)

        engine = EconomicsEngine()
        sale = await engine.execute_dataset_sale(
            db_session, block.block_id, "buyer_inc", 500.0, platform_fee_pct=0.10,
        )
        await db_session.commit()

        assert sale.platform_fee == pytest.approx(50.0, rel=0.01)
        assert sale.distributable == pytest.approx(450.0, rel=0.01)
        assert sale.sale_price == 500.0

    async def test_low_reputation_excluded(self, db_session: AsyncSession):
        """Nodes below min_reputation get zero payout."""
        # Create a block where one node has reputation far below min_reputation (0.1)
        low_node = await _make_node(db_session, "low_rep_node", reputation=0.05)
        good_node = await _make_node(db_session, "good_rep_node", reputation=1.0)
        block = await _make_block(db_session, "lowrep_block", status="solved")

        await _make_attempt(db_session, "lr_att_1", block.block_id, low_node.node_id,
                            score=0.5, output_json={"grid": [[1]]})
        await _make_attempt(db_session, "lr_att_2", block.block_id, good_node.node_id,
                            score=0.8, output_json={"grid": [[2]]})

        await _make_reward(db_session, block.block_id, low_node.node_id, "solver", 50.0)
        await _make_reward(db_session, block.block_id, good_node.node_id, "exploration", 50.0)
        await db_session.commit()

        engine = EconomicsEngine()
        sale = await engine.execute_dataset_sale(
            db_session, block.block_id, "buyer_xyz", 200.0,
        )
        await db_session.commit()

        payouts = sale.payout_summary["payouts"]
        payout_map = {p["node_id"]: p for p in payouts}

        assert payout_map["low_rep_node"]["final_payout"] == 0.0
        assert payout_map["low_rep_node"]["penalty_reason"] == "below_min_reputation"
        assert payout_map["good_rep_node"]["final_payout"] > 0.0

    async def test_sale_creates_artifact(self, db_session: AsyncSession):
        """A BlockArtifact with type 'dataset_sale' is created."""
        block, nodes, rewards = await _setup_finalized_block_with_rewards(db_session)

        engine = EconomicsEngine()
        await engine.execute_dataset_sale(
            db_session, block.block_id, "buyer_art", 300.0,
        )
        await db_session.commit()

        result = await db_session.execute(
            select(BlockArtifact).where(
                BlockArtifact.block_id == block.block_id,
                BlockArtifact.artifact_type == "dataset_sale",
            )
        )
        artifact = result.scalar_one_or_none()

        assert artifact is not None
        assert artifact.artifact_json["buyer"] == "buyer_art"
        assert artifact.artifact_json["sale_price"] == 300.0
        assert "payouts" in artifact.artifact_json

    async def test_sale_creates_reward_records(self, db_session: AsyncSession):
        """Reward records with type 'dataset_sale' are created for each paid node."""
        block, nodes, rewards = await _setup_finalized_block_with_rewards(db_session)

        engine = EconomicsEngine()
        sale = await engine.execute_dataset_sale(
            db_session, block.block_id, "buyer_rec", 1000.0,
        )
        await db_session.commit()

        result = await db_session.execute(
            select(Reward).where(
                Reward.block_id == block.block_id,
                Reward.reward_type == "dataset_sale",
            )
        )
        sale_rewards = list(result.scalars().all())

        # At least the nodes that got payouts should have reward records
        paid_nodes = {p["node_id"] for p in sale.payout_summary["payouts"]
                      if p["final_payout"] > 0}
        rewarded_nodes = {r.node_id for r in sale_rewards}
        assert paid_nodes == rewarded_nodes

        # All reward amounts are positive
        for r in sale_rewards:
            assert r.reward_amount > 0
            assert r.reward_type == "dataset_sale"

    async def test_sale_on_non_finalized_block_fails(self, db_session: AsyncSession):
        """Attempting a sale on an 'open' block raises ValueError."""
        await _make_node(db_session, "nonfin_node")
        block = await _make_block(db_session, "nonfin_block", status="open")
        await db_session.commit()

        engine = EconomicsEngine()
        with pytest.raises(ValueError, match="not finalized"):
            await engine.execute_dataset_sale(
                db_session, block.block_id, "buyer_bad", 100.0,
            )


# ===========================================================================
# TestEconomicsAPI
# ===========================================================================


@pytest.mark.asyncio
class TestEconomicsAPI:
    """HTTP endpoint tests for the economics router."""

    async def test_dataset_sale_endpoint(self, test_client, db_session: AsyncSession):
        """POST /economics/dataset-sale executes a sale end-to-end."""
        block, nodes, rewards = await _setup_finalized_block_with_rewards(
            db_session, block_id="api_sale_block",
        )

        resp = await test_client.post("/economics/dataset-sale", json={
            "block_id": "api_sale_block",
            "buyer": "api_buyer",
            "sale_price": 500.0,
            "platform_fee_pct": 0.10,
        })

        assert resp.status_code == 200
        data = resp.json()
        assert data["block_id"] == "api_sale_block"
        assert data["buyer"] == "api_buyer"
        assert data["sale_price"] == 500.0
        assert data["platform_fee"] == pytest.approx(50.0, rel=0.01)
        assert data["distributable"] == pytest.approx(450.0, rel=0.01)
        assert data["status"] == "completed"
        assert data["payout_count"] >= 1
        assert "payouts" in data["payout_summary"]

    async def test_leaderboard_endpoint(self, test_client, db_session: AsyncSession):
        """GET /economics/leaderboard returns nodes ordered by reputation."""
        await _make_node(db_session, "api_lb_low", reputation=0.3)
        await _make_node(db_session, "api_lb_mid", reputation=1.1)
        await _make_node(db_session, "api_lb_top", reputation=1.9)
        await db_session.commit()

        resp = await test_client.get("/economics/leaderboard")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 3

        # Verify ordering — first entry has highest reputation
        reps = [entry["reputation_score"] for entry in data]
        assert reps == sorted(reps, reverse=True)
        assert data[0]["node_id"] == "api_lb_top"

    async def test_economic_stats_endpoint(self, test_client, db_session: AsyncSession):
        """GET /economics/stats returns aggregated economic data."""
        # Seed some data
        node = await _make_node(db_session, "api_stats_node", reputation=1.0)
        block = await _make_block(db_session, "api_stats_block", status="solved")
        await _make_reward(db_session, block.block_id, node.node_id, "solver", 42.0)
        await db_session.commit()

        resp = await test_client.get("/economics/stats")

        assert resp.status_code == 200
        data = resp.json()
        assert "total_rewards_distributed" in data
        assert data["total_rewards_distributed"] >= 42.0
        assert "rewards_by_type" in data
        assert "dataset_sales" in data
        assert "nodes" in data
        assert data["nodes"]["active"] >= 1
        assert data["nodes"]["avg_reputation"] > 0
