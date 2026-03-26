"""Block controller — the orchestrator of the reasoning ledger.

The controller manages the lifecycle of blocks:
- ranks attempts
- prunes weak candidates
- promotes strong ones
- triggers finality checks
- seals completed blocks

Search becomes data. Elimination becomes integrity.
"""
import asyncio
import logging
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from swarmchain.db.engine import async_session_factory
from swarmchain.db.models import Block, Attempt
from swarmchain.services.finality import FinalityService
from swarmchain.services.reward_engine import RewardEngine
from swarmchain.services.domain_validators import ValidatorRunner
from swarmchain.services.reputation import ReputationService
from swarmchain.config import get_settings

logger = logging.getLogger("swarmchain.controller")


class BlockController:
    """Manages block lifecycle — prune, promote, finalize, seal."""

    def __init__(self):
        s = get_settings()
        self.beam_width = s.beam_width
        self.prune_threshold = s.prune_threshold
        self.loop_interval = s.controller_loop_interval_sec
        self._running = False
        self.reward_engine = RewardEngine()
        self.reputation_service = ReputationService()

    async def process_block(self, db: AsyncSession, block: Block) -> str | None:
        """Process a single open block — prune, promote, check finality.

        Returns new status if changed, else None.
        """
        if block.status != "open":
            return None

        # Check for solved
        if await FinalityService.check_solved(db, block):
            await self._finalize_block(db, block)
            return "solved"

        # Check for exhausted
        if await FinalityService.check_exhausted(db, block):
            await self._finalize_block(db, block)
            return "exhausted"

        # Prune and promote
        await self._prune_and_promote(db, block)
        return None

    async def _prune_and_promote(self, db: AsyncSession, block: Block) -> None:
        """Rank attempts, promote top candidates, prune weak ones.

        Beam search: keep top N promoted, prune bottom scorers below threshold.
        Failed attempts with elimination signal are not discarded from the record.
        """
        # Get all non-pruned attempts ordered by score
        result = await db.execute(
            select(Attempt)
            .where(Attempt.block_id == block.block_id)
            .where(Attempt.pruned == False)
            .where(Attempt.valid == True)
            .order_by(Attempt.score.desc())
        )
        attempts = list(result.scalars().all())

        if not attempts:
            return

        # Promote top beam_width
        for i, attempt in enumerate(attempts):
            if i < self.beam_width:
                attempt.promoted = True
            else:
                attempt.promoted = False

        # Prune below threshold (but only if we have enough attempts)
        if len(attempts) > self.beam_width * 2:
            for attempt in attempts:
                if attempt.score < self.prune_threshold and not attempt.promoted:
                    attempt.pruned = True

        await db.flush()

    async def _finalize_block(self, db: AsyncSession, block: Block) -> None:
        """Seal the block, run domain validator, compute rewards, generate artifacts."""
        logger.info(f"Finalizing block {block.block_id} — status: {block.status}")

        # Run domain validator (if one exists for this domain)
        winning_attempt = None
        if block.winning_attempt_id:
            result = await db.execute(
                select(Attempt).where(Attempt.attempt_id == block.winning_attempt_id)
            )
            winning_attempt = result.scalar_one_or_none()

        decision = await ValidatorRunner.run_validator(
            db, block, winning_attempt, block.final_score or 0.0
        )
        if decision:
            logger.info(
                f"Block {block.block_id}: validator={decision.validator_name} "
                f"verdict={decision.verdict} confidence={decision.confidence:.3f}"
            )

        # Seal and generate artifact
        await FinalityService.seal_block(db, block)

        # Compute rewards
        rewards = await self.reward_engine.compute_rewards(db, block)
        logger.info(f"Block {block.block_id}: {len(rewards)} rewards distributed")

        # Update reputations
        rep_updates = await self.reputation_service.update_after_block(db, block.block_id)
        logger.info(f"Block {block.block_id}: {len(rep_updates)} node reputations updated")

        await db.flush()

    async def run_loop(self) -> None:
        """Background controller loop — processes all open blocks periodically."""
        self._running = True
        logger.info("Controller loop started")

        while self._running:
            try:
                async with async_session_factory() as db:
                    result = await db.execute(
                        select(Block).where(Block.status == "open")
                    )
                    open_blocks = list(result.scalars().all())

                    for block in open_blocks:
                        new_status = await self.process_block(db, block)
                        if new_status:
                            logger.info(f"Block {block.block_id} → {new_status}")

                    await db.commit()

            except Exception as e:
                logger.error(f"Controller loop error: {e}", exc_info=True)

            await asyncio.sleep(self.loop_interval)

    def stop(self) -> None:
        self._running = False
