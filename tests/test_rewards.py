"""Tests for RewardEngine — reward impact, not participation."""
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from swarmchain.db.models import Block, Attempt, Node, Reward, LineageEdge, new_id
from swarmchain.services.reward_engine import RewardEngine
from swarmchain.services.lineage import LineageService


async def _setup_block_with_attempts(
    db: AsyncSession,
    block_id: str = "rwdblock001",
    include_lineage: bool = True,
) -> tuple[Block, list[Node], list[Attempt]]:
    """Create a finalized block with multiple nodes and attempts.

    Returns (block, nodes, attempts).
    Attempts:
      - node_a: attempt_a1 (root, score=0.3)
      - node_a: attempt_a2 (child of a1, score=0.6)
      - node_b: attempt_b1 (child of a2, score=1.0) — WINNER
      - node_c: attempt_c1 (explorer, score=0.5)
    """
    # Nodes
    node_a = Node(node_id="rwd_node_a", node_type="gpu", hardware_class="rtx4090")
    node_b = Node(node_id="rwd_node_b", node_type="gpu", hardware_class="a100")
    node_c = Node(node_id="rwd_node_c", node_type="cpu", hardware_class="xeon")
    db.add_all([node_a, node_b, node_c])
    await db.flush()

    # Block (finalized, solved)
    block = Block(
        block_id=block_id,
        task_id="arc-001-fill-blue",
        domain="arc",
        reward_pool=100.0,
        status="solved",
        winning_attempt_id="rwd_att_b1",
        winning_node_id="rwd_node_b",
        final_score=1.0,
        attempt_count=4,
        total_energy=7.0,
        task_payload={"expected_output": [[1, 1], [1, 1]]},
    )
    db.add(block)
    await db.flush()

    # Attempts
    att_a1 = Attempt(
        attempt_id="rwd_att_a1",
        block_id=block_id,
        node_id="rwd_node_a",
        method="random",
        strategy_family="brute_force",
        output_json={"grid": [[0, 0], [0, 0]]},
        score=0.3,
        valid=True,
        energy_cost=1.0,
        latency_ms=100,
    )
    att_a2 = Attempt(
        attempt_id="rwd_att_a2",
        block_id=block_id,
        node_id="rwd_node_a",
        parent_attempt_id="rwd_att_a1",
        method="refined",
        strategy_family="gradient",
        output_json={"grid": [[1, 0], [1, 0]]},
        score=0.6,
        valid=True,
        energy_cost=2.0,
        latency_ms=200,
    )
    att_b1 = Attempt(
        attempt_id="rwd_att_b1",
        block_id=block_id,
        node_id="rwd_node_b",
        parent_attempt_id="rwd_att_a2",
        method="exact",
        strategy_family="solver",
        output_json={"grid": [[1, 1], [1, 1]]},
        score=1.0,
        valid=True,
        energy_cost=3.0,
        latency_ms=300,
    )
    att_c1 = Attempt(
        attempt_id="rwd_att_c1",
        block_id=block_id,
        node_id="rwd_node_c",
        method="heuristic",
        strategy_family="explorer",
        output_json={"grid": [[1, 1], [0, 0]]},
        score=0.5,
        valid=True,
        energy_cost=1.0,
        latency_ms=50,
    )
    db.add_all([att_a1, att_a2, att_b1, att_c1])
    await db.flush()

    # Lineage edges: a1 -> a2 -> b1
    if include_lineage:
        edge1 = LineageEdge(
            block_id=block_id,
            parent_attempt_id="rwd_att_a1",
            child_attempt_id="rwd_att_a2",
            delta_score=0.3,
        )
        edge2 = LineageEdge(
            block_id=block_id,
            parent_attempt_id="rwd_att_a2",
            child_attempt_id="rwd_att_b1",
            delta_score=0.4,
        )
        db.add_all([edge1, edge2])
        await db.flush()

    nodes = [node_a, node_b, node_c]
    attempts = [att_a1, att_a2, att_b1, att_c1]
    return block, nodes, attempts


@pytest.mark.asyncio
class TestRewardEngineComputeRewards:
    """RewardEngine.compute_rewards distributes pool across reward types."""

    async def test_compute_rewards_returns_rewards(self, db_session: AsyncSession):
        block, nodes, attempts = await _setup_block_with_attempts(db_session)
        engine = RewardEngine()
        rewards = await engine.compute_rewards(db_session, block)
        assert len(rewards) > 0
        assert all(isinstance(r, Reward) for r in rewards)

    async def test_total_rewards_do_not_exceed_pool(self, db_session: AsyncSession):
        block, nodes, attempts = await _setup_block_with_attempts(db_session)
        engine = RewardEngine()
        rewards = await engine.compute_rewards(db_session, block)
        total = sum(r.reward_amount for r in rewards)
        assert total <= block.reward_pool + 0.01  # float tolerance


@pytest.mark.asyncio
class TestSolverReward:
    """Solver gets 40% of the pool."""

    async def test_solver_gets_40_percent(self, db_session: AsyncSession):
        block, nodes, attempts = await _setup_block_with_attempts(db_session)
        engine = RewardEngine()
        rewards = await engine.compute_rewards(db_session, block)

        solver_rewards = [r for r in rewards if r.reward_type == "solver"]
        assert len(solver_rewards) == 1
        assert solver_rewards[0].node_id == "rwd_node_b"
        assert solver_rewards[0].reward_amount == pytest.approx(40.0, rel=1e-3)

    async def test_solver_score_basis_is_1(self, db_session: AsyncSession):
        block, nodes, attempts = await _setup_block_with_attempts(db_session)
        engine = RewardEngine()
        rewards = await engine.compute_rewards(db_session, block)

        solver = [r for r in rewards if r.reward_type == "solver"][0]
        assert solver.score_basis == pytest.approx(1.0)


@pytest.mark.asyncio
class TestLineageReward:
    """Lineage ancestors get 30% of the pool, split by score."""

    async def test_lineage_ancestors_get_30_percent(self, db_session: AsyncSession):
        block, nodes, attempts = await _setup_block_with_attempts(db_session)
        engine = RewardEngine()
        rewards = await engine.compute_rewards(db_session, block)

        lineage_rewards = [r for r in rewards if r.reward_type == "lineage"]
        total_lineage = sum(r.reward_amount for r in lineage_rewards)
        assert total_lineage == pytest.approx(30.0, rel=1e-3)

    async def test_lineage_split_by_score(self, db_session: AsyncSession):
        block, nodes, attempts = await _setup_block_with_attempts(db_session)
        engine = RewardEngine()
        rewards = await engine.compute_rewards(db_session, block)

        lineage_rewards = {r.node_id: r for r in rewards if r.reward_type == "lineage"}
        # Ancestry: a1 (0.3) -> a2 (0.6) -> b1 (winner, excluded from lineage)
        # node_a owns both a1 and a2, total ancestor score = 0.3 + 0.6 = 0.9
        # a1 share: (0.3/0.9) * 30 = 10.0
        # a2 share: (0.6/0.9) * 30 = 20.0
        # Both belong to rwd_node_a, but they are separate Reward rows
        lineage_list = [r for r in rewards if r.reward_type == "lineage"]
        a1_reward = next(r for r in lineage_list if r.score_basis == pytest.approx(0.3, rel=1e-2))
        a2_reward = next(r for r in lineage_list if r.score_basis == pytest.approx(0.6, rel=1e-2))
        assert a1_reward.reward_amount == pytest.approx(30.0 * 0.3 / 0.9, rel=1e-2)
        assert a2_reward.reward_amount == pytest.approx(30.0 * 0.6 / 0.9, rel=1e-2)

    async def test_winner_excluded_from_lineage(self, db_session: AsyncSession):
        block, nodes, attempts = await _setup_block_with_attempts(db_session)
        engine = RewardEngine()
        rewards = await engine.compute_rewards(db_session, block)

        lineage_rewards = [r for r in rewards if r.reward_type == "lineage"]
        lineage_attempt_scores = [r.score_basis for r in lineage_rewards]
        # Winner (score 1.0) should not appear in lineage rewards
        assert 1.0 not in lineage_attempt_scores


@pytest.mark.asyncio
class TestExplorationReward:
    """Exploration gets 20% for non-winning, non-lineage attempts."""

    async def test_exploration_gets_20_percent(self, db_session: AsyncSession):
        block, nodes, attempts = await _setup_block_with_attempts(db_session)
        engine = RewardEngine()
        rewards = await engine.compute_rewards(db_session, block)

        exploration_rewards = [r for r in rewards if r.reward_type == "exploration"]
        total_exploration = sum(r.reward_amount for r in exploration_rewards)
        assert total_exploration == pytest.approx(20.0, rel=1e-3)

    async def test_exploration_goes_to_explorer_node(self, db_session: AsyncSession):
        block, nodes, attempts = await _setup_block_with_attempts(db_session)
        engine = RewardEngine()
        rewards = await engine.compute_rewards(db_session, block)

        exploration_rewards = [r for r in rewards if r.reward_type == "exploration"]
        # att_c1 (node_c, score 0.5) is the only non-lineage, non-winner attempt
        explorer_nodes = {r.node_id for r in exploration_rewards}
        assert "rwd_node_c" in explorer_nodes


@pytest.mark.asyncio
class TestEfficiencyReward:
    """Efficiency gets 10% — best score-per-energy ratio."""

    async def test_efficiency_gets_10_percent(self, db_session: AsyncSession):
        block, nodes, attempts = await _setup_block_with_attempts(db_session)
        engine = RewardEngine()
        rewards = await engine.compute_rewards(db_session, block)

        efficiency_rewards = [r for r in rewards if r.reward_type == "efficiency"]
        total_efficiency = sum(r.reward_amount for r in efficiency_rewards)
        assert total_efficiency == pytest.approx(10.0, rel=1e-3)

    async def test_efficiency_favors_high_score_low_energy(self, db_session: AsyncSession):
        block, nodes, attempts = await _setup_block_with_attempts(db_session)
        engine = RewardEngine()
        rewards = await engine.compute_rewards(db_session, block)

        efficiency_rewards = [r for r in rewards if r.reward_type == "efficiency"]
        # att_c1: score=0.5, energy=1.0 -> eff=0.50
        # att_b1: score=1.0, energy=3.0 -> eff=0.33
        # att_a2: score=0.6, energy=2.0 -> eff=0.30
        # att_a1: score=0.3, energy=1.0 -> eff=0.30
        # node_c should get the largest efficiency reward share
        node_c_eff = [r for r in efficiency_rewards if r.node_id == "rwd_node_c"]
        node_b_eff = [r for r in efficiency_rewards if r.node_id == "rwd_node_b"]
        if node_c_eff and node_b_eff:
            assert node_c_eff[0].reward_amount > node_b_eff[0].reward_amount


@pytest.mark.asyncio
class TestRewardNodeUpdate:
    """Reward engine updates node total_rewards."""

    async def test_node_totals_updated(self, db_session: AsyncSession):
        block, nodes, attempts = await _setup_block_with_attempts(db_session)
        engine = RewardEngine()
        await engine.compute_rewards(db_session, block)
        await db_session.commit()

        # Refresh nodes
        for node in nodes:
            await db_session.refresh(node)

        # Each node should have received some reward
        # node_b: solver + efficiency
        assert nodes[1].total_rewards > 0
        # node_a: lineage + efficiency
        assert nodes[0].total_rewards > 0
        # node_c: exploration + efficiency
        assert nodes[2].total_rewards > 0
