"""Pydantic schemas for Block operations."""
from datetime import datetime
from pydantic import BaseModel, Field


class BlockOpen(BaseModel):
    """Request to open a new reasoning block."""
    task_id: str
    domain: str = "arc"
    reward_pool: float = 100.0
    max_attempts: int = 500
    time_limit_sec: int = 3600
    task_payload: dict = Field(default_factory=dict)
    metadata: dict | None = None


class BlockResponse(BaseModel):
    """Full block representation."""
    block_id: str
    task_id: str
    domain: str
    status: str
    reward_pool: float
    max_attempts: int
    time_limit_sec: int
    start_time: datetime
    end_time: datetime | None
    total_energy: float
    attempt_count: int
    winning_attempt_id: str | None
    winning_node_id: str | None
    final_score: float | None
    elimination_summary: dict | None
    task_payload: dict
    metadata: dict | None

    model_config = {"from_attributes": True}


class BlockListResponse(BaseModel):
    blocks: list[BlockResponse]
    total: int


class BlockFinalize(BaseModel):
    """Manual finalization request."""
    force: bool = False
    reason: str | None = None
