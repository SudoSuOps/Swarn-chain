#!/usr/bin/env python3
"""SwarmChain Single-Chain Testnet Controller — 1000-block canonical protocol test.

One open block at a time. All miners attack the same block. Shared elimination
becomes reasoning. Search becomes data.

This is a CLIENT-SIDE orchestrator that uses the existing SwarmChain API.
The backend handles scoring, rewards, cost accounting, convergence, and anchoring.
This script enforces the single-chain discipline and the search escalation ladder.

Usage:
    python single_chain.py \
      --api-url http://165.227.109.67/api \
      --api-key <key> \
      --session-id testnet-001 \
      --blocks 1000 \
      --resume
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

# ── ARCTaskGenerator import from backend ─────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from swarmchain.tasks.arc_generator import ARCTaskGenerator

# ── Logging ──────────────────────────────────────────────────────────────────

LOG_FORMAT = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
log = logging.getLogger("single-chain")

# ── Constants ────────────────────────────────────────────────────────────────

TESTNET_DIR = Path("/data2/swarmchain/testnet")
STATE_FILE = TESTNET_DIR / "single_chain_state.json"
ATTEMPTS_LEDGER = TESTNET_DIR / "attempts.jsonl"
BLOCKS_LEDGER = TESTNET_DIR / "blocks.jsonl"
CONVERGENCE_LEDGER = TESTNET_DIR / "convergence.jsonl"

HONEY_THRESHOLD = 0.95
JELLY_THRESHOLD = 0.30

# Model endpoint configuration
XEON_FLEET_PORTS = list(range(9100, 9125))  # 25 servers
CAPITAL_9B_PORT = 8090
BASE_9B_PORT = 8091
WHALE_7B_HOST = "192.168.0.99"
WHALE_7B_PORT = 8092
SIGEDGE_HOST = "192.168.0.79"
SIGEDGE_PORT = 8085

# Model endpoints — all OpenAI-compatible /v1/chat/completions
XEON_FLEET_BASE = "http://localhost"
CAPITAL_9B_URL = f"http://localhost:{CAPITAL_9B_PORT}/v1/chat/completions"
BASE_9B_URL = f"http://localhost:{BASE_9B_PORT}/v1/chat/completions"
WHALE_7B_URL = f"http://{WHALE_7B_HOST}:{WHALE_7B_PORT}/v1/chat/completions"
SIGEDGE_URL = f"http://{SIGEDGE_HOST}:{SIGEDGE_PORT}/v1/chat/completions"

# Convergence and anchoring intervals
CONVERGENCE_INTERVAL = 20
ANCHOR_INTERVAL = 50

# Retry configuration
MAX_API_RETRIES = 5
API_RETRY_BASE_DELAY = 1.0
MODEL_TIMEOUT = 120.0
API_TIMEOUT = 60.0
MAX_MODEL_TOKENS = 4096


# ── Curriculum ───────────────────────────────────────────────────────────────

def build_curriculum(total_blocks: int) -> list[dict]:
    """Generate the 1000-block curriculum from the ARCTaskGenerator.

    Returns a list of dicts, each containing the task plus block metadata:
      sequence_number, task_id, tier, difficulty_band, attempt_cap, task (full payload)
    """
    gen = ARCTaskGenerator()
    curriculum: list[dict] = []

    # Blocks 1-100: Tier 1 deterministic, 24 attempts
    tier1_a = gen.generate_catalog(100, base_seed=10000)
    for i, task in enumerate(tier1_a):
        seq = i + 1
        if seq > total_blocks:
            return curriculum
        curriculum.append({
            "sequence_number": seq,
            "task_id": task["task_id"],
            "tier": 1,
            "difficulty_band": "deterministic",
            "attempt_cap": 24,
            "task": task,
        })

    # Blocks 101-200: Tier 1 deterministic, 16 attempts
    tier1_b = gen.generate_catalog(100, base_seed=10100)
    for i, task in enumerate(tier1_b):
        seq = 101 + i
        if seq > total_blocks:
            return curriculum
        curriculum.append({
            "sequence_number": seq,
            "task_id": task["task_id"],
            "tier": 1,
            "difficulty_band": "deterministic_hard",
            "attempt_cap": 16,
            "task": task,
        })

    # Blocks 201-450: Tier 2 simple composition, 24 attempts
    tier2_a = gen.generate_tier2_catalog(250, base_seed=20000)
    for i, task in enumerate(tier2_a):
        seq = 201 + i
        if seq > total_blocks:
            return curriculum
        curriculum.append({
            "sequence_number": seq,
            "task_id": task["task_id"],
            "tier": 2,
            "difficulty_band": "simple_composition",
            "attempt_cap": 24,
            "task": task,
        })

    # Blocks 451-700: Tier 2 multi-step composition, 32 attempts
    tier2_b = gen.generate_tier2_catalog(250, base_seed=20250)
    for i, task in enumerate(tier2_b):
        seq = 451 + i
        if seq > total_blocks:
            return curriculum
        curriculum.append({
            "sequence_number": seq,
            "task_id": task["task_id"],
            "tier": 2,
            "difficulty_band": "multi_step_composition",
            "attempt_cap": 32,
            "task": task,
        })

    # Blocks 701-1000: Tier 3 relational, 40 attempts
    tier3 = gen.generate_tier3_catalog(300, base_seed=50000)
    for i, task in enumerate(tier3):
        seq = 701 + i
        if seq > total_blocks:
            return curriculum
        curriculum.append({
            "sequence_number": seq,
            "task_id": task["task_id"],
            "tier": 3,
            "difficulty_band": "relational",
            "attempt_cap": 40,
            "task": task,
        })

    return curriculum


# ── Prompt Building ──────────────────────────────────────────────────────────

def build_prompt(task: dict, context: dict | None = None) -> str:
    """Build an ARC grid task prompt.

    Args:
        task: Full task dict with description, input_grid, expected_output.
        context: Optional dict with best_score and best_grid for escalation phases.
    """
    desc = task.get("description", "Transform the grid")
    input_grid = task.get("input_grid", [])

    prompt = (
        f"You solve ARC grid transformation tasks.\n\n"
        f"Task: {desc}\n\n"
        f"Input grid:\n{json.dumps(input_grid)}\n\n"
        f"Output ONLY the transformed grid as a JSON array of arrays. No explanation.\n\n"
    )

    if context and context.get("best_score") is not None:
        prompt += (
            f"Previous best attempt scored {context['best_score']:.3f}:\n"
            f"{json.dumps(context['best_grid'])}\n\n"
            f"Improve on this. Output ONLY the corrected grid.\n\n"
        )

    prompt += "Output grid:"
    return prompt


# ── Grid Parsing ─────────────────────────────────────────────────────────────

def parse_grid_response(response: str) -> list[list[int]] | None:
    """Parse a model response into a grid. Handles JSON, markdown blocks, regex."""
    text = response.strip()
    if not text:
        return None

    # Try direct JSON parse
    try:
        grid = json.loads(text)
        if isinstance(grid, list) and all(isinstance(row, list) for row in grid):
            return [[int(c) for c in row] for row in grid]
    except (json.JSONDecodeError, ValueError, TypeError):
        pass

    # Try extracting from markdown code blocks
    for marker in ["```json", "```"]:
        if marker in text:
            start = text.index(marker) + len(marker)
            rest = text[start:]
            end_idx = rest.find("```")
            if end_idx != -1:
                candidate = rest[:end_idx].strip()
            else:
                candidate = rest.strip()
            try:
                grid = json.loads(candidate)
                if isinstance(grid, list) and all(isinstance(row, list) for row in grid):
                    return [[int(c) for c in row] for row in grid]
            except (json.JSONDecodeError, ValueError, TypeError):
                pass

    # Try regex for array pattern
    match = re.search(r'\[\s*\[.*?\]\s*\]', text, re.DOTALL)
    if match:
        try:
            grid = json.loads(match.group())
            if isinstance(grid, list) and all(isinstance(row, list) for row in grid):
                return [[int(c) for c in row] for row in grid]
        except (json.JSONDecodeError, ValueError, TypeError):
            pass

    return None


# ── Model Client ─────────────────────────────────────────────────────────────

async def call_model(
    client: httpx.AsyncClient,
    url: str,
    prompt: str,
    model_name: str = "default",
    max_tokens: int = MAX_MODEL_TOKENS,
    temperature: float = 0.7,
) -> str:
    """Call an OpenAI-compatible model endpoint. Returns raw response text.

    Handles both /v1/chat/completions and /v1/completions.
    Retries on 503/429 with exponential backoff.
    """
    is_chat = "/chat/" in url

    if is_chat:
        payload = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
    else:
        payload = {
            "model": model_name,
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

    last_error = None
    for attempt in range(MAX_API_RETRIES):
        try:
            resp = await client.post(url, json=payload, timeout=MODEL_TIMEOUT)
            if resp.status_code == 200:
                data = resp.json()
                if is_chat:
                    return data["choices"][0]["message"]["content"]
                else:
                    return data["choices"][0]["text"]
            elif resp.status_code in (503, 429, 502):
                delay = API_RETRY_BASE_DELAY * (2 ** attempt)
                log.warning(
                    "Model %s returned %d, retry %d/%d in %.1fs",
                    url.split("/")[2] if "/" in url else url,
                    resp.status_code, attempt + 1, MAX_API_RETRIES, delay,
                )
                await asyncio.sleep(delay)
                last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
            else:
                log.warning("Model call to %s failed: %d %s", url, resp.status_code, resp.text[:200])
                return ""
        except httpx.TimeoutException:
            delay = API_RETRY_BASE_DELAY * (2 ** attempt)
            log.warning("Model call to %s timed out, retry %d/%d", url, attempt + 1, MAX_API_RETRIES)
            await asyncio.sleep(delay)
            last_error = "timeout"
        except Exception as e:
            log.error("Model call to %s error: %s", url, e)
            return ""

    log.error("Model call to %s exhausted retries: %s", url, last_error)
    return ""


# ── API Client ───────────────────────────────────────────────────────────────

class SwarmChainAPI:
    """Client for the SwarmChain backend API with retry logic."""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            headers = {}
            if self.api_key:
                headers["X-API-Key"] = self.api_key
            self._client = httpx.AsyncClient(
                headers=headers,
                timeout=API_TIMEOUT,
                limits=httpx.Limits(max_connections=100, max_keepalive_connections=50),
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def _request(self, method: str, path: str, **kwargs) -> dict | list | None:
        """Make an API request with retry logic."""
        client = await self._get_client()
        url = f"{self.base_url}{path}"
        last_error = None

        for attempt in range(MAX_API_RETRIES):
            try:
                resp = await client.request(method, url, **kwargs)
                if resp.status_code == 200:
                    return resp.json()
                elif resp.status_code in (503, 429, 502):
                    delay = API_RETRY_BASE_DELAY * (2 ** attempt)
                    log.warning(
                        "API %s %s returned %d, retry %d/%d in %.1fs",
                        method, path, resp.status_code, attempt + 1, MAX_API_RETRIES, delay,
                    )
                    await asyncio.sleep(delay)
                    last_error = f"HTTP {resp.status_code}"
                else:
                    log.error("API %s %s failed: %d %s", method, path, resp.status_code, resp.text[:300])
                    return None
            except httpx.TimeoutException:
                delay = API_RETRY_BASE_DELAY * (2 ** attempt)
                log.warning("API %s %s timed out, retry %d/%d", method, path, attempt + 1, MAX_API_RETRIES)
                await asyncio.sleep(delay)
                last_error = "timeout"
            except Exception as e:
                log.error("API %s %s error: %s", method, path, e)
                return None

        log.error("API %s %s exhausted retries: %s", method, path, last_error)
        return None

    async def register_node(self, node_id: str, node_type: str, hardware_class: str, metadata: dict | None = None) -> dict | None:
        return await self._request("POST", "/nodes/register", json={
            "node_id": node_id,
            "node_type": node_type,
            "hardware_class": hardware_class,
            "metadata": metadata or {},
        })

    async def open_block(self, task_id: str, task_payload: dict, max_attempts: int, metadata: dict | None = None) -> dict | None:
        return await self._request("POST", "/blocks/open", json={
            "task_id": task_id,
            "domain": "arc",
            "reward_pool": 100.0,
            "max_attempts": max_attempts,
            "time_limit_sec": 3600,
            "task_payload": task_payload,
            "metadata": metadata or {},
        })

    async def get_block(self, block_id: str) -> dict | None:
        return await self._request("GET", f"/blocks/{block_id}")

    async def finalize_block(self, block_id: str, force: bool = False) -> dict | None:
        return await self._request("POST", f"/blocks/{block_id}/finalize", json={
            "force": force,
            "reason": "single-chain controller: block sealed",
        })

    async def get_block_anatomy(self, block_id: str) -> dict | None:
        return await self._request("GET", f"/blocks/{block_id}/anatomy")

    async def submit_attempt(
        self,
        block_id: str,
        node_id: str,
        grid: list[list[int]],
        raw_response: str,
        strategy_family: str,
        energy_cost: float,
        latency_ms: int,
        parent_attempt_id: str | None = None,
    ) -> dict | None:
        return await self._request("POST", "/attempts", json={
            "node_id": node_id,
            "block_id": block_id,
            "parent_attempt_id": parent_attempt_id,
            "method": "llm_inference",
            "strategy_family": strategy_family,
            "output_json": {"grid": grid, "raw_response": raw_response[:500]},
            "energy_cost": energy_cost,
            "latency_ms": latency_ms,
        })

    async def get_top_attempts(self, block_id: str, limit: int = 10) -> dict | None:
        return await self._request("GET", f"/attempts/block/{block_id}/top", params={"limit": limit})

    async def trigger_anchor(self, window_size: int = 50) -> dict | None:
        return await self._request("POST", "/anchors/trigger", params={"window_size": window_size})

    async def send_energy_report(self) -> dict | None:
        return await self._request("POST", "/economics/energy-report")


# ── Energy Metering ──────────────────────────────────────────────────────────

class EnergyMeter:
    """Simplified energy metering for the orchestrator.

    Since this controller dispatches to remote model endpoints, energy is estimated
    from wall time + hardware class rather than local process CPU time.
    """

    # Approximate watts per hardware class
    POWER_DRAW = {
        "xeon-72t": 10.0,      # Share of CPU per worker (TDP ~350W / 25 workers ≈ 14W, but idle mix)
        "qwen-4b-cpu": 10.0,   # SwarmBuddy on edge
        "capital-9b": 150.0,   # GPU inference (RTX PRO 6000 share)
        "base-9b": 150.0,      # Base 9B on RTX PRO 6000
        "whale-7b": 200.0,     # 7B Instruct on RTX 3090
    }

    @staticmethod
    def estimate(wall_seconds: float, hardware_class: str) -> dict:
        """Estimate energy from wall time and hardware class.

        Returns:
            {"energy_cost": float, "wall_ms": int, "cpu_seconds": float, "gpu_seconds": float}
        """
        power = EnergyMeter.POWER_DRAW.get(hardware_class, 10.0)
        energy = power * wall_seconds  # watt-seconds (joules)
        is_gpu = hardware_class in ("capital-9b", "base-9b", "whale-7b")

        return {
            "energy_cost": round(energy, 4),
            "wall_ms": int(wall_seconds * 1000),
            "cpu_seconds": 0.0 if is_gpu else round(wall_seconds, 4),
            "gpu_seconds": round(wall_seconds, 4) if is_gpu else 0.0,
        }


# ── Worker Dispatch ──────────────────────────────────────────────────────────

class WorkerDispatcher:
    """Dispatches inference calls to model endpoints and submits results to SwarmChain."""

    def __init__(self, api: SwarmChainAPI, session_id: str):
        self.api = api
        self.session_id = session_id
        self._model_client: httpx.AsyncClient | None = None

    async def _get_model_client(self) -> httpx.AsyncClient:
        if self._model_client is None or self._model_client.is_closed:
            self._model_client = httpx.AsyncClient(
                timeout=MODEL_TIMEOUT,
                limits=httpx.Limits(max_connections=100, max_keepalive_connections=50),
            )
        return self._model_client

    async def close(self):
        if self._model_client and not self._model_client.is_closed:
            await self._model_client.aclose()

    async def dispatch_single(
        self,
        block_id: str,
        task: dict,
        node_id: str,
        model_url: str,
        model_name: str,
        hardware_class: str,
        strategy: str,
        context: dict | None = None,
        parent_attempt_id: str | None = None,
        temperature: float = 0.7,
    ) -> dict | None:
        """Dispatch a single inference call to a model endpoint and submit to SwarmChain.

        Returns the attempt receipt dict or None on failure.
        """
        prompt = build_prompt(task, context)
        client = await self._get_model_client()

        start_time = time.monotonic()
        start_iso = datetime.now(timezone.utc).isoformat()

        response_text = await call_model(
            client, model_url, prompt,
            model_name=model_name,
            max_tokens=MAX_MODEL_TOKENS,
            temperature=temperature,
        )

        wall_elapsed = time.monotonic() - start_time
        end_iso = datetime.now(timezone.utc).isoformat()

        # Parse grid
        grid = parse_grid_response(response_text)
        if grid is None:
            grid = []

        # Estimate energy
        energy = EnergyMeter.estimate(wall_elapsed, hardware_class)

        # Submit attempt to API
        result = await self.api.submit_attempt(
            block_id=block_id,
            node_id=node_id,
            grid=grid,
            raw_response=response_text[:500] if response_text else "",
            strategy_family=f"model:{model_name}/{strategy}",
            energy_cost=energy["energy_cost"],
            latency_ms=energy["wall_ms"],
            parent_attempt_id=parent_attempt_id,
        )

        if result is None:
            return None

        score = result.get("score", 0.0)
        attempt_id = result.get("attempt_id", "unknown")

        # Build receipt
        if score >= HONEY_THRESHOLD:
            tier_result = "HONEY"
        elif score >= JELLY_THRESHOLD:
            tier_result = "JELLY"
        else:
            tier_result = "PROPOLIS"

        receipt = {
            "session_id": self.session_id,
            "sequence_number": task.get("_sequence_number", 0),
            "block_id": block_id,
            "attempt_id": attempt_id,
            "parent_attempt_id": parent_attempt_id,
            "task_id": task.get("task_id", "unknown"),
            "tier": task.get("tier", 0),
            "difficulty_band": task.get("_difficulty_band", "unknown"),
            "node_id": node_id,
            "model_name": model_name,
            "strategy": strategy,
            "score": score,
            "tier_result": tier_result,
            "start_time": start_iso,
            "end_time": end_iso,
            "wall_ms": energy["wall_ms"],
            "cpu_seconds": energy["cpu_seconds"],
            "gpu_seconds": energy["gpu_seconds"],
            "energy_cost": energy["energy_cost"],
            "api_cost": 0.0,
            "total_cost": round(energy["energy_cost"] * 0.10 / 3600, 8),
        }

        return receipt

    async def dispatch_xeon_fleet(
        self,
        block_id: str,
        task: dict,
        count: int = 25,
        context: dict | None = None,
        parent_attempt_id: str | None = None,
    ) -> list[dict]:
        """Dispatch to all 25 xeon miners in parallel.

        Returns list of attempt receipts (filtering out failures).
        """
        tasks = []
        for i, port in enumerate(XEON_FLEET_PORTS[:count]):
            node_id = f"xeon-miner-{i:03d}"
            url = f"{XEON_FLEET_BASE}:{port}/v1/chat/completions"
            strategy = "xeon_search" if context is None else "xeon_refine"
            tasks.append(
                self.dispatch_single(
                    block_id=block_id,
                    task=task,
                    node_id=node_id,
                    model_url=url,
                    model_name="qwen-4b",
                    hardware_class="xeon-72t",
                    strategy=strategy,
                    context=context,
                    parent_attempt_id=parent_attempt_id,
                )
            )

        results = await asyncio.gather(*tasks, return_exceptions=True)
        receipts = []
        for r in results:
            if isinstance(r, dict):
                receipts.append(r)
            elif isinstance(r, Exception):
                log.warning("Xeon dispatch error: %s", r)
        return receipts

    async def dispatch_sigedge(
        self,
        block_id: str,
        task: dict,
        context: dict | None = None,
        parent_attempt_id: str | None = None,
    ) -> dict | None:
        """Dispatch to SwarmBuddy on sigedge (Jetson Orin)."""
        return await self.dispatch_single(
            block_id=block_id,
            task=task,
            node_id="sigedge-jetson",
            model_url=SIGEDGE_URL,
            model_name="qwen-4b-edge",
            hardware_class="qwen-4b-cpu",
            strategy="edge_search" if context is None else "edge_refine",
            context=context,
            parent_attempt_id=parent_attempt_id,
        )

    async def dispatch_capital(
        self,
        block_id: str,
        task: dict,
        context: dict | None = None,
        parent_attempt_id: str | None = None,
    ) -> dict | None:
        """Dispatch to Capital-9B on GPU."""
        return await self.dispatch_single(
            block_id=block_id,
            task=task,
            node_id="capital-9b",
            model_url=CAPITAL_9B_URL,
            model_name="capital-9b",
            hardware_class="capital-9b",
            strategy="capital_compose" if context is None else "capital_refine",
            context=context,
            parent_attempt_id=parent_attempt_id,
            temperature=0.5,
        )

    async def dispatch_base9b(
        self,
        block_id: str,
        task: dict,
        context: dict | None = None,
        parent_id: str | None = None,
    ) -> dict | None:
        """Dispatch to Base 9B competitor — same size as Capital, zero training."""
        return await self.dispatch_single(
            block_id=block_id,
            task=task,
            node_id="base-9b",
            model_url=BASE_9B_URL,
            model_name="base-9b",
            hardware_class="base-9b",
            strategy="base9b_compete",
            context=context,
            parent_attempt_id=parent_id,
        )

    async def dispatch_whale7b(
        self,
        block_id: str,
        task: dict,
        context: dict | None = None,
        parent_id: str | None = None,
    ) -> dict | None:
        """Dispatch to Whale 7B challenger — smaller, cheaper, on 3090."""
        return await self.dispatch_single(
            block_id=block_id,
            task=task,
            node_id="whale-7b",
            model_url=WHALE_7B_URL,
            model_name="whale-7b",
            hardware_class="whale-7b",
            strategy="whale7b_challenge",
            context=context,
            parent_attempt_id=parent_id,
        )

    async def dispatch_atlas(
        self,
        block_id: str,
        task: dict,
        context: dict | None = None,
        parent_attempt_id: str | None = None,
    ) -> dict | None:
        """Dispatch to Atlas-27B specialist."""
        return await self.dispatch_single(
            block_id=block_id,
            task=task,
            node_id="atlas-27b",
            model_url=ATLAS_27B_URL,
            model_name="atlas-27b",
            hardware_class="atlas-27b",
            strategy="atlas_specialist",
            context=context,
            parent_attempt_id=parent_attempt_id,
            temperature=0.3,
        )


# ── State Management ─────────────────────────────────────────────────────────

class TestnetState:
    """Persistent state for the single-chain testnet run."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.last_completed_block = 0
        self.blocks_solved = 0
        self.blocks_exhausted = 0
        self.total_attempts = 0
        self.total_energy = 0.0
        self.saved_at = ""

    def save(self):
        """Save state to disk."""
        data = {
            "session_id": self.session_id,
            "last_completed_block": self.last_completed_block,
            "blocks_solved": self.blocks_solved,
            "blocks_exhausted": self.blocks_exhausted,
            "total_attempts": self.total_attempts,
            "total_energy": round(self.total_energy, 4),
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }
        STATE_FILE.write_text(json.dumps(data, indent=2) + "\n")

    @classmethod
    def load(cls, session_id: str) -> "TestnetState":
        """Load state from disk if it exists and matches session_id."""
        state = cls(session_id)
        if STATE_FILE.exists():
            try:
                data = json.loads(STATE_FILE.read_text())
                if data.get("session_id") == session_id:
                    state.last_completed_block = data.get("last_completed_block", 0)
                    state.blocks_solved = data.get("blocks_solved", 0)
                    state.blocks_exhausted = data.get("blocks_exhausted", 0)
                    state.total_attempts = data.get("total_attempts", 0)
                    state.total_energy = data.get("total_energy", 0.0)
                    state.saved_at = data.get("saved_at", "")
                    log.info(
                        "Resumed state: last_block=%d solved=%d exhausted=%d attempts=%d",
                        state.last_completed_block, state.blocks_solved,
                        state.blocks_exhausted, state.total_attempts,
                    )
                else:
                    log.warning(
                        "State file session mismatch: got %s, expected %s. Starting fresh.",
                        data.get("session_id"), session_id,
                    )
            except (json.JSONDecodeError, KeyError) as e:
                log.warning("Failed to load state file: %s. Starting fresh.", e)
        return state


# ── Ledger Writers ───────────────────────────────────────────────────────────

def append_jsonl(path: Path, record: dict):
    """Append a single JSON record to a JSONL file."""
    with open(path, "a") as f:
        f.write(json.dumps(record, default=str) + "\n")


# ── Convergence Window ───────────────────────────────────────────────────────

def compute_convergence_window(blocks_data: list[dict], window_start: int, window_end: int) -> dict:
    """Compute convergence metrics from the last N blocks of block anatomy data.

    Args:
        blocks_data: List of block anatomy/artifact dicts from blocks.jsonl (most recent N).
        window_start: First block sequence number in window.
        window_end: Last block sequence number in window.

    Returns:
        Convergence window dict.
    """
    total = len(blocks_data)
    if total == 0:
        return {
            "window": f"{window_start}-{window_end}",
            "total_blocks": 0,
            "solve_rate": 0.0,
            "attempts_per_solve": 0.0,
            "cost_per_honey": 0.0,
            "energy_per_honey": 0.0,
            "propolis_ratio": 0.0,
        }

    solved = sum(1 for b in blocks_data if b.get("status") == "solved")
    total_attempts = sum(b.get("attempt_count", 0) for b in blocks_data)
    total_energy = sum(b.get("total_energy", 0) for b in blocks_data)

    # Count propolis attempts from receipts
    propolis_count = sum(b.get("propolis_count", 0) for b in blocks_data)

    solve_rate = solved / total if total > 0 else 0.0
    attempts_per_solve = total_attempts / max(solved, 1)
    energy_per_honey = total_energy / max(solved, 1)
    cost_per_honey = energy_per_honey * 0.10 / 3600  # approximate $/honey
    propolis_ratio = propolis_count / max(total_attempts, 1)

    return {
        "window": f"{window_start}-{window_end}",
        "total_blocks": total,
        "blocks_solved": solved,
        "blocks_exhausted": total - solved,
        "total_attempts": total_attempts,
        "total_energy": round(total_energy, 4),
        "solve_rate": round(solve_rate, 4),
        "attempts_per_solve": round(attempts_per_solve, 2),
        "cost_per_honey": round(cost_per_honey, 6),
        "energy_per_honey": round(energy_per_honey, 2),
        "propolis_ratio": round(propolis_ratio, 4),
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }


# ── Node Registration ───────────────────────────────────────────────────────

async def register_all_nodes(api: SwarmChainAPI):
    """Register all worker nodes with the SwarmChain API."""
    nodes = []

    # 25 xeon miners
    for i in range(25):
        nodes.append(("xeon-miner-%03d" % i, "cpu-worker", "xeon-72t"))

    # Edge node
    nodes.append(("sigedge-jetson", "edge-jetson", "jetson-orin-8gb"))

    # Capital 9B
    nodes.append(("capital-9b", "gpu-mid", "rtx-pro-6000"))

    # Atlas 27B
    nodes.append(("base-9b", "gpu-compete", "rtx-pro-6000"))
    nodes.append(("whale-7b", "gpu-mid", "rtx-3090"))

    registered = 0
    for node_id, node_type, hw_class in nodes:
        result = await api.register_node(
            node_id=node_id,
            node_type=node_type,
            hardware_class=hw_class,
            metadata={
                "session": "single-chain-testnet",
                "registered_by": "single_chain.py",
            },
        )
        if result:
            registered += 1

    log.info("Registered %d/%d nodes", registered, len(nodes))
    return registered


# ── Search Escalation Ladder ─────────────────────────────────────────────────

async def mine_block(
    dispatcher: WorkerDispatcher,
    api: SwarmChainAPI,
    block_id: str,
    block_entry: dict,
    state: TestnetState,
) -> dict:
    """Execute the full search escalation ladder for a single block.

    Returns a block result dict with status, attempts used, best score, solver info,
    and the full elimination trace.

    The four phases:
      Phase 1 (first 30%): Cheap deterministic search — xeon fleet + sigedge
      Phase 2 (next 30%): Compositional / structured — Capital-9B on promoted candidates
      Phase 3 (next 20%): Mutation / refinement — perturb best attempt
      Phase 4 (final 20%): GPU competition — Base-9B + Whale-7B + Capital-9B race (if jelly exists)
    """
    task = block_entry["task"]
    attempt_cap = block_entry["attempt_cap"]
    seq = block_entry["sequence_number"]
    tier = block_entry["tier"]
    band = block_entry["difficulty_band"]

    # Inject metadata into task for receipt building
    task["_sequence_number"] = seq
    task["_difficulty_band"] = band

    # Phase budgets
    phase1_budget = max(1, int(attempt_cap * 0.30))
    phase2_budget = max(1, int(attempt_cap * 0.30))
    phase3_budget = max(1, int(attempt_cap * 0.20))
    phase4_budget = max(1, attempt_cap - phase1_budget - phase2_budget - phase3_budget)

    # Tracking
    all_receipts: list[dict] = []
    best_score = 0.0
    best_grid: list[list[int]] | None = None
    best_attempt_id: str | None = None
    best_node_id: str | None = None
    best_strategy: str | None = None
    solved = False
    elimination_trace: list[dict] = []
    block_start = time.monotonic()

    def record_receipts(receipts: list[dict], phase: str) -> bool:
        """Process receipts, update best, check for honey. Returns True if solved."""
        nonlocal best_score, best_grid, best_attempt_id, best_node_id, best_strategy, solved

        for receipt in receipts:
            all_receipts.append(receipt)
            append_jsonl(ATTEMPTS_LEDGER, receipt)

            score = receipt.get("score", 0.0)
            if score > best_score:
                best_score = score
                best_attempt_id = receipt.get("attempt_id")
                best_node_id = receipt.get("node_id")
                best_strategy = receipt.get("strategy")
                # Reconstruct best grid from the output
                # (We don't store the full grid in receipt — query the API if needed)
                # For escalation context, we'll use the API to get top attempts

            if score >= HONEY_THRESHOLD:
                solved = True
                elimination_trace.append({
                    "phase": phase,
                    "event": "SOLVED",
                    "score": score,
                    "node_id": receipt.get("node_id"),
                    "strategy": receipt.get("strategy"),
                    "attempt_id": receipt.get("attempt_id"),
                })
                return True

        return False

    async def get_best_context() -> tuple[dict | None, str | None]:
        """Fetch the best attempts from the API for escalation context."""
        top = await api.get_top_attempts(block_id, limit=3)
        if top and top.get("attempts"):
            best = top["attempts"][0]
            best_grid_ctx = best.get("output_json", {}).get("grid")
            if best_grid_ctx:
                return {
                    "best_score": best.get("score", 0.0),
                    "best_grid": best_grid_ctx,
                }, best.get("attempt_id")
        return None, None

    # ── Phase 1: Cheap deterministic search ──────────────────────────────
    log.debug("[Block %d] Phase 1: Cheap search (%d budget)", seq, phase1_budget)
    elimination_trace.append({
        "phase": "phase1_deterministic",
        "event": "START",
        "budget": phase1_budget,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    # Dispatch xeon fleet (up to budget) + sigedge in parallel
    xeon_count = min(25, phase1_budget - 1)  # Reserve 1 for sigedge
    if xeon_count < 1:
        xeon_count = min(25, phase1_budget)

    fleet_task = dispatcher.dispatch_xeon_fleet(block_id, task, count=xeon_count)
    edge_task = dispatcher.dispatch_sigedge(block_id, task)

    fleet_receipts, edge_receipt = await asyncio.gather(fleet_task, edge_task, return_exceptions=True)

    phase1_receipts: list[dict] = []
    if isinstance(fleet_receipts, list):
        phase1_receipts.extend(fleet_receipts)
    elif isinstance(fleet_receipts, Exception):
        log.warning("[Block %d] Xeon fleet error: %s", seq, fleet_receipts)

    if isinstance(edge_receipt, dict):
        phase1_receipts.append(edge_receipt)
    elif isinstance(edge_receipt, Exception):
        log.warning("[Block %d] Sigedge error: %s", seq, edge_receipt)

    elimination_trace.append({
        "phase": "phase1_deterministic",
        "event": "COMPLETE",
        "attempts": len(phase1_receipts),
        "best_score": max((r.get("score", 0) for r in phase1_receipts), default=0),
        "strategies_tried": list(set(r.get("strategy", "") for r in phase1_receipts)),
    })

    if record_receipts(phase1_receipts, "phase1_deterministic"):
        # Block solved in Phase 1
        pass
    elif len(all_receipts) >= attempt_cap:
        solved = False
    else:
        # ── Phase 2: Compositional / structured ──────────────────────────
        log.debug("[Block %d] Phase 2: Compositional (%d budget)", seq, phase2_budget)
        elimination_trace.append({
            "phase": "phase2_compositional",
            "event": "START",
            "budget": phase2_budget,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        context, parent_id = await get_best_context()
        phase2_receipts: list[dict] = []
        phase2_remaining = min(phase2_budget, attempt_cap - len(all_receipts))

        if phase2_remaining > 0:
            # ALL 3 GPU models race in parallel — Capital-9B vs Base-9B vs Whale-7B
            # Plus xeon fleet for volume. Everyone competes for the solve.
            xeon_phase2_count = max(0, phase2_remaining - 3)  # Reserve 3 for GPU race

            # GPU race: all 3 models get the same context, compete in parallel
            gpu_race = await asyncio.gather(
                dispatcher.dispatch_capital(
                    block_id, task, context=context, parent_attempt_id=parent_id,
                ),
                dispatcher.dispatch_base9b(
                    block_id, task, context=context, parent_id=parent_id,
                ),
                dispatcher.dispatch_whale7b(
                    block_id, task, context=context, parent_id=parent_id,
                ),
                return_exceptions=True,
            )
            for r in gpu_race:
                if isinstance(r, dict):
                    phase2_receipts.append(r)
                    if r.get("score", 0) > best_score:
                        context, parent_id = await get_best_context()

            # Check if any GPU solved it
            if not any(r.get("score", 0) >= HONEY_THRESHOLD for r in phase2_receipts if isinstance(r, dict)):
                # Parallel xeon fleet for volume (remainder of phase 2)
                remaining_slots = min(xeon_phase2_count, attempt_cap - len(all_receipts) - len(phase2_receipts))
                if remaining_slots > 0:
                    xeon_receipts = await dispatcher.dispatch_xeon_fleet(
                        block_id, task, count=min(25, remaining_slots),
                        context=context, parent_attempt_id=parent_id,
                    )
                    phase2_receipts.extend(xeon_receipts)

        elimination_trace.append({
            "phase": "phase2_compositional",
            "event": "COMPLETE",
            "attempts": len(phase2_receipts),
            "best_score": max((r.get("score", 0) for r in phase2_receipts), default=0),
        })

        if record_receipts(phase2_receipts, "phase2_compositional"):
            pass
        elif len(all_receipts) >= attempt_cap:
            solved = False
        else:
            # ── Phase 3: Mutation / refinement ───────────────────────────
            log.debug("[Block %d] Phase 3: Mutation (%d budget)", seq, phase3_budget)
            elimination_trace.append({
                "phase": "phase3_mutation",
                "event": "START",
                "budget": phase3_budget,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

            context, parent_id = await get_best_context()
            phase3_receipts: list[dict] = []
            phase3_remaining = min(phase3_budget, attempt_cap - len(all_receipts))

            if phase3_remaining > 0 and context:
                # Capital-9B refines the best attempt
                for _ in range(min(2, phase3_remaining)):
                    if len(all_receipts) + len(phase3_receipts) >= attempt_cap:
                        break
                    receipt = await dispatcher.dispatch_capital(
                        block_id, task, context=context, parent_attempt_id=parent_id,
                    )
                    if receipt:
                        phase3_receipts.append(receipt)
                        if receipt.get("score", 0) >= HONEY_THRESHOLD:
                            break
                        if receipt.get("score", 0) > best_score:
                            context, parent_id = await get_best_context()

                # Xeon fleet with mutation context
                xeon_remaining = min(
                    phase3_remaining - len(phase3_receipts),
                    attempt_cap - len(all_receipts) - len(phase3_receipts),
                )
                if xeon_remaining > 0 and not any(r.get("score", 0) >= HONEY_THRESHOLD for r in phase3_receipts):
                    xeon_receipts = await dispatcher.dispatch_xeon_fleet(
                        block_id, task, count=min(25, xeon_remaining),
                        context=context, parent_attempt_id=parent_id,
                    )
                    phase3_receipts.extend(xeon_receipts)

            elif phase3_remaining > 0:
                # No good context yet, keep cheap searching
                xeon_receipts = await dispatcher.dispatch_xeon_fleet(
                    block_id, task, count=min(25, phase3_remaining),
                )
                phase3_receipts.extend(xeon_receipts)

            elimination_trace.append({
                "phase": "phase3_mutation",
                "event": "COMPLETE",
                "attempts": len(phase3_receipts),
                "best_score": max((r.get("score", 0) for r in phase3_receipts), default=0),
            })

            if record_receipts(phase3_receipts, "phase3_mutation"):
                pass
            elif len(all_receipts) >= attempt_cap:
                solved = False
            else:
                # ── Phase 4: Specialist rescue ───────────────────────────
                log.debug("[Block %d] Phase 4: Specialist (%d budget)", seq, phase4_budget)
                elimination_trace.append({
                    "phase": "phase4_specialist",
                    "event": "START",
                    "budget": phase4_budget,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

                context, parent_id = await get_best_context()
                phase4_receipts: list[dict] = []
                phase4_remaining = min(phase4_budget, attempt_cap - len(all_receipts))

                # Dispatch all GPU competitors in parallel — they race for the solve
                use_gpus = best_score > 0.3  # lower threshold, let them compete

                if phase4_remaining > 0 and use_gpus and context:
                    # All 3 GPU models compete: Base 9B + Whale 7B + Capital-9B refine
                    gpu_tasks = []
                    gpu_tasks.append(dispatcher.dispatch_base9b(
                        block_id, task, context=context, parent_id=parent_id,
                    ))
                    gpu_tasks.append(dispatcher.dispatch_whale7b(
                        block_id, task, context=context, parent_id=parent_id,
                    ))
                    gpu_tasks.append(dispatcher.dispatch_capital(
                        block_id, task, context=context, parent_attempt_id=parent_id,
                    ))
                    gpu_results = await asyncio.gather(*gpu_tasks, return_exceptions=True)
                    for r in gpu_results:
                        if isinstance(r, dict):
                            phase4_receipts.append(r)

                    # If Atlas didn't solve, spend remaining on Capital refinement
                    if not any(r.get("score", 0) >= HONEY_THRESHOLD for r in phase4_receipts):
                        remaining = min(
                            phase4_remaining - len(phase4_receipts),
                            attempt_cap - len(all_receipts) - len(phase4_receipts),
                        )
                        for _ in range(min(2, remaining)):
                            receipt = await dispatcher.dispatch_capital(
                                block_id, task, context=context, parent_attempt_id=parent_id,
                            )
                            if receipt:
                                phase4_receipts.append(receipt)
                                if receipt.get("score", 0) >= HONEY_THRESHOLD:
                                    break
                                context, parent_id = await get_best_context()
                elif phase4_remaining > 0:
                    # No jelly — don't waste Atlas; just run more xeon
                    xeon_receipts = await dispatcher.dispatch_xeon_fleet(
                        block_id, task, count=min(25, phase4_remaining),
                        context=context, parent_attempt_id=parent_id,
                    )
                    phase4_receipts.extend(xeon_receipts)

                elimination_trace.append({
                    "phase": "phase4_specialist",
                    "event": "COMPLETE",
                    "attempts": len(phase4_receipts),
                    "atlas_used": use_atlas,
                    "best_score": max((r.get("score", 0) for r in phase4_receipts), default=0),
                })

                record_receipts(phase4_receipts, "phase4_specialist")

    # ── Block outcome ────────────────────────────────────────────────────
    block_wall = time.monotonic() - block_start
    total_energy = sum(r.get("energy_cost", 0) for r in all_receipts)
    attempt_count = len(all_receipts)

    # Recompute best from all receipts (in case record_receipts missed grid update)
    for r in all_receipts:
        if r.get("score", 0) > best_score:
            best_score = r["score"]
            best_attempt_id = r.get("attempt_id")
            best_node_id = r.get("node_id")
            best_strategy = r.get("strategy")
            solved = best_score >= HONEY_THRESHOLD

    propolis_count = sum(1 for r in all_receipts if r.get("tier_result") == "PROPOLIS")
    jelly_count = sum(1 for r in all_receipts if r.get("tier_result") == "JELLY")
    honey_count = sum(1 for r in all_receipts if r.get("tier_result") == "HONEY")

    status = "solved" if solved else "exhausted"

    return {
        "block_id": block_id,
        "sequence_number": seq,
        "task_id": task.get("task_id", "unknown"),
        "tier": tier,
        "difficulty_band": band,
        "attempt_cap": attempt_cap,
        "status": status,
        "solved": solved,
        "best_score": best_score,
        "best_attempt_id": best_attempt_id,
        "best_node_id": best_node_id,
        "best_strategy": best_strategy,
        "attempt_count": attempt_count,
        "total_energy": round(total_energy, 4),
        "wall_seconds": round(block_wall, 2),
        "propolis_count": propolis_count,
        "jelly_count": jelly_count,
        "honey_count": honey_count,
        "elimination_trace": elimination_trace,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }


# ── Main Controller ──────────────────────────────────────────────────────────

async def run_testnet(args: argparse.Namespace):
    """Main testnet loop — generates curriculum, mines blocks one at a time."""
    session_id = args.session_id
    total_blocks = args.blocks

    log.info("=" * 72)
    log.info("SwarmChain Single-Chain Testnet Controller")
    log.info("Session: %s | Blocks: %d", session_id, total_blocks)
    log.info("API: %s", args.api_url)
    log.info("=" * 72)

    # Build curriculum
    log.info("Generating %d-block curriculum...", total_blocks)
    curriculum = build_curriculum(total_blocks)
    log.info("Curriculum ready: %d blocks across tiers 1-3", len(curriculum))

    if len(curriculum) < total_blocks:
        log.warning(
            "Curriculum only generated %d blocks (requested %d). Running with %d.",
            len(curriculum), total_blocks, len(curriculum),
        )
        total_blocks = len(curriculum)

    # Load or initialize state
    if args.resume:
        state = TestnetState.load(session_id)
    else:
        state = TestnetState(session_id)

    start_block = state.last_completed_block
    if start_block > 0:
        log.info("Resuming from block %d", start_block + 1)

    # Initialize API client and worker dispatcher
    api = SwarmChainAPI(args.api_url, args.api_key)
    dispatcher = WorkerDispatcher(api, session_id)

    try:
        # Register all nodes
        await register_all_nodes(api)

        # Recent block data for convergence windows
        recent_blocks: list[dict] = []

        # Track overall timing
        testnet_start = time.monotonic()

        # ── Main loop: one block at a time ───────────────────────────────
        for block_entry in curriculum:
            seq = block_entry["sequence_number"]

            # Skip already-completed blocks on resume
            if seq <= start_block:
                continue

            task = block_entry["task"]
            task_id = block_entry["task_id"]
            tier = block_entry["tier"]
            band = block_entry["difficulty_band"]
            attempt_cap = block_entry["attempt_cap"]

            # Step 1: Open block via API
            block_resp = await api.open_block(
                task_id=task_id,
                task_payload={
                    "input_grid": task["input_grid"],
                    "expected_output": task["expected_output"],
                    "description": task["description"],
                },
                max_attempts=attempt_cap,
                metadata={
                    "session_id": session_id,
                    "sequence_number": seq,
                    "tier": tier,
                    "difficulty_band": band,
                    "attempt_cap": attempt_cap,
                },
            )

            if block_resp is None:
                log.error("[Block %d/%d] Failed to open block for %s. Skipping.", seq, total_blocks, task_id)
                continue

            block_id = block_resp["block_id"]

            # Step 2: Mine the block through the escalation ladder
            block_result = await mine_block(dispatcher, api, block_id, block_entry, state)

            # Step 3: Finalize the block via API
            finalize_resp = await api.finalize_block(block_id, force=True)
            if finalize_resp is None:
                log.warning("[Block %d/%d] Finalize call failed for %s", seq, total_blocks, block_id)

            # Step 4: Get block anatomy artifact and enrich
            anatomy = await api.get_block_anatomy(block_id)
            block_artifact = {
                "session_id": session_id,
                "sequence_number": seq,
                "tier": tier,
                "difficulty_band": band,
                "block_id": block_id,
                "task_id": task_id,
                "status": block_result["status"],
                "best_score": block_result["best_score"],
                "attempt_count": block_result["attempt_count"],
                "total_energy": block_result["total_energy"],
                "wall_seconds": block_result["wall_seconds"],
                "propolis_count": block_result["propolis_count"],
                "jelly_count": block_result["jelly_count"],
                "honey_count": block_result["honey_count"],
                "best_node_id": block_result["best_node_id"],
                "best_strategy": block_result["best_strategy"],
                "elimination_trace": block_result["elimination_trace"],
                "anatomy": anatomy,
                "completed_at": block_result["completed_at"],
            }
            append_jsonl(BLOCKS_LEDGER, block_artifact)
            recent_blocks.append(block_artifact)

            # Keep only last CONVERGENCE_INTERVAL blocks in memory
            if len(recent_blocks) > CONVERGENCE_INTERVAL:
                recent_blocks = recent_blocks[-CONVERGENCE_INTERVAL:]

            # Step 5: Update state
            state.last_completed_block = seq
            state.total_attempts += block_result["attempt_count"]
            state.total_energy += block_result["total_energy"]
            if block_result["solved"]:
                state.blocks_solved += 1
            else:
                state.blocks_exhausted += 1
            state.save()

            # Step 6: Progress output
            status_str = "SOLVED" if block_result["solved"] else "EXHAUSTED"
            solver_info = ""
            if block_result["solved"] and block_result["best_node_id"]:
                solver_info = f" by {block_result['best_node_id']} [{block_result['best_strategy']}]"

            log.info(
                "[Block %d/%d] %s (Tier %d, %d att) -> %s in %d attempts "
                "(score=%.3f, energy=%.0f, %.1fs)%s",
                seq, total_blocks, task_id, tier, attempt_cap,
                status_str, block_result["attempt_count"],
                block_result["best_score"], block_result["total_energy"],
                block_result["wall_seconds"], solver_info,
            )

            # Step 7: Convergence window every 20 blocks
            if seq % CONVERGENCE_INTERVAL == 0:
                window_start = seq - CONVERGENCE_INTERVAL + 1
                window_end = seq
                convergence = compute_convergence_window(recent_blocks, window_start, window_end)
                append_jsonl(CONVERGENCE_LEDGER, convergence)

                # Compute delta from previous window if we have enough data
                delta_str = ""
                if seq >= 2 * CONVERGENCE_INTERVAL:
                    # Read previous convergence record from file to compare
                    try:
                        prev_records = []
                        with open(CONVERGENCE_LEDGER, "r") as f:
                            for line in f:
                                try:
                                    prev_records.append(json.loads(line))
                                except json.JSONDecodeError:
                                    pass
                        if len(prev_records) >= 2:
                            prev_cost = prev_records[-2].get("cost_per_honey", 0)
                            curr_cost = convergence.get("cost_per_honey", 0)
                            delta = curr_cost - prev_cost
                            arrow = "^" if delta > 0 else "v" if delta < 0 else "="
                            delta_str = f" delta={delta:+.6f} {arrow}"
                    except Exception:
                        pass

                log.info(
                    "[Convergence %d-%d] solve=%.0f%% att/solve=%.1f cost/honey=$%.6f%s",
                    window_start, window_end,
                    convergence["solve_rate"] * 100,
                    convergence["attempts_per_solve"],
                    convergence["cost_per_honey"],
                    delta_str,
                )

                # Send energy report
                await api.send_energy_report()

            # Step 8: Hedera anchor every 50 blocks
            if seq % ANCHOR_INTERVAL == 0:
                log.info("[Anchor] Triggering Hedera anchor at block %d", seq)
                anchor_result = await api.trigger_anchor(window_size=ANCHOR_INTERVAL)
                if anchor_result:
                    log.info(
                        "[Anchor] %s — merkle_root=%s",
                        anchor_result.get("status", "unknown"),
                        anchor_result.get("receipt", {}).get("merkle_root", "n/a")[:16] + "...",
                    )
                else:
                    log.warning("[Anchor] Failed to trigger at block %d", seq)

        # ── Final Report ─────────────────────────────────────────────────
        testnet_wall = time.monotonic() - testnet_start
        total_completed = state.blocks_solved + state.blocks_exhausted

        log.info("=" * 72)
        log.info("TESTNET COMPLETE")
        log.info("=" * 72)
        log.info("Session:         %s", session_id)
        log.info("Blocks:          %d completed", total_completed)
        log.info("Solved:          %d (%.1f%%)", state.blocks_solved,
                 state.blocks_solved / max(total_completed, 1) * 100)
        log.info("Exhausted:       %d (%.1f%%)", state.blocks_exhausted,
                 state.blocks_exhausted / max(total_completed, 1) * 100)
        log.info("Total attempts:  %d", state.total_attempts)
        log.info("Total energy:    %.2f J", state.total_energy)
        log.info("Wall time:       %.1f min", testnet_wall / 60)
        log.info("Att/solve:       %.1f", state.total_attempts / max(state.blocks_solved, 1))
        log.info("Energy/solve:    %.2f J", state.total_energy / max(state.blocks_solved, 1))
        log.info("Cost/solve:      $%.6f", state.total_energy * 0.10 / 3600 / max(state.blocks_solved, 1))
        log.info("-" * 72)
        log.info("Ledgers:")
        log.info("  Attempts:      %s", ATTEMPTS_LEDGER)
        log.info("  Blocks:        %s", BLOCKS_LEDGER)
        log.info("  Convergence:   %s", CONVERGENCE_LEDGER)
        log.info("  State:         %s", STATE_FILE)
        log.info("=" * 72)

        # Write final report as JSON
        final_report = {
            "session_id": session_id,
            "total_blocks": total_completed,
            "blocks_solved": state.blocks_solved,
            "blocks_exhausted": state.blocks_exhausted,
            "solve_rate": round(state.blocks_solved / max(total_completed, 1), 4),
            "total_attempts": state.total_attempts,
            "total_energy": round(state.total_energy, 4),
            "wall_time_min": round(testnet_wall / 60, 2),
            "attempts_per_solve": round(state.total_attempts / max(state.blocks_solved, 1), 2),
            "energy_per_solve": round(state.total_energy / max(state.blocks_solved, 1), 2),
            "cost_per_solve": round(state.total_energy * 0.10 / 3600 / max(state.blocks_solved, 1), 8),
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
        report_path = TESTNET_DIR / "final_report.json"
        report_path.write_text(json.dumps(final_report, indent=2) + "\n")
        log.info("Final report: %s", report_path)

    except KeyboardInterrupt:
        log.info("Interrupted by user. State saved at block %d.", state.last_completed_block)
        state.save()
    except Exception as e:
        log.error("Fatal error: %s", e)
        log.error(traceback.format_exc())
        state.save()
        raise
    finally:
        await dispatcher.close()
        await api.close()


# ── CLI ──────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="SwarmChain Single-Chain Testnet Controller — 1000-block canonical protocol test",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full 1000-block testnet
  python single_chain.py --api-url http://165.227.109.67/api --api-key <key> --session-id testnet-001

  # Resume after interruption
  python single_chain.py --api-url http://165.227.109.67/api --api-key <key> --session-id testnet-001 --resume

  # Quick 50-block test
  python single_chain.py --api-url http://165.227.109.67/api --api-key <key> --session-id test-50 --blocks 50
        """,
    )
    parser.add_argument(
        "--api-url", required=True,
        help="SwarmChain API base URL (e.g. http://165.227.109.67/api)",
    )
    parser.add_argument(
        "--api-key", default="",
        help="API key for authenticated endpoints",
    )
    parser.add_argument(
        "--session-id", default="testnet-001",
        help="Unique session identifier for this testnet run",
    )
    parser.add_argument(
        "--blocks", type=int, default=1000,
        help="Total number of blocks to mine (default: 1000)",
    )
    parser.add_argument(
        "--resume", action="store_true",
        help="Resume from last saved state",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # Ensure output directory exists
    TESTNET_DIR.mkdir(parents=True, exist_ok=True)

    log.info("Starting SwarmChain single-chain testnet...")
    asyncio.run(run_testnet(args))


if __name__ == "__main__":
    main()
