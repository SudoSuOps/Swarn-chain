"""Centralized configuration for SwarmChain backend."""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://swarmchain:swarmchain@localhost:5432/swarmchain"
    database_url_sync: str = "postgresql://swarmchain:swarmchain@localhost:5432/swarmchain"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Controller
    controller_loop_interval_sec: float = 5.0
    beam_width: int = 10
    prune_threshold: float = 0.05
    min_contribution_score: float = 0.01

    # Reward engine
    solver_reward_pct: float = 0.40
    lineage_reward_pct: float = 0.30
    exploration_reward_pct: float = 0.20
    efficiency_reward_pct: float = 0.10

    # Economics
    spam_score_threshold: float = 0.02
    spam_penalty_multiplier: float = 0.1
    duplicate_decay_rate: float = 0.5
    reputation_solve_boost: float = 0.05
    reputation_spam_penalty: float = 0.1
    reputation_decay_rate: float = 0.001
    min_reputation_for_rewards: float = 0.1

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_key: str = ""  # empty = no auth required (dev mode)
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    model_config = {"env_prefix": "SWARMCHAIN_", "env_file": ".env"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
