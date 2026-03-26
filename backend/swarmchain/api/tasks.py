"""Tasks API — procedurally generated ARC task catalog.

Exposes the deterministic ARC task generator over HTTP:
  GET /tasks       — list tasks (paginated, filterable)
  GET /tasks/stats — catalog summary statistics
  GET /tasks/{id}  — full task payload by ID
"""
from __future__ import annotations

from collections import Counter
from fastapi import APIRouter, HTTPException, Query

from swarmchain.tasks.arc_generator import ARCTaskGenerator, TRANSFORM_TYPES

router = APIRouter()

# Singleton generator — stateless, deterministic
_generator = ARCTaskGenerator()

# Default catalog: 1000 tasks starting from seed 42
_CATALOG_COUNT = 1000
_CATALOG_BASE_SEED = 42

# Lazy-loaded catalog cache (generated once on first access)
_catalog_cache: list[dict] | None = None
_catalog_index: dict[str, dict] | None = None


def _get_catalog() -> list[dict]:
    """Return the cached catalog, generating it on first call."""
    global _catalog_cache
    if _catalog_cache is None:
        _catalog_cache = _generator.generate_catalog(
            count=_CATALOG_COUNT, base_seed=_CATALOG_BASE_SEED
        )
    return _catalog_cache


def _get_index() -> dict[str, dict]:
    """Return task_id -> task dict index for O(1) lookup."""
    global _catalog_index
    if _catalog_index is None:
        _catalog_index = {t["task_id"]: t for t in _get_catalog()}
    return _catalog_index


# ---------------------------------------------------------------------------
# Stats endpoint MUST be defined before the {task_id} path parameter route,
# otherwise FastAPI will try to match "stats" as a task_id.
# ---------------------------------------------------------------------------


@router.get("/stats")
async def tasks_stats():
    """Catalog summary: total count, transform distribution, grid size distribution."""
    catalog = _get_catalog()

    # Transform type distribution
    transform_dist: dict[str, int] = Counter(t["transform_type"] for t in catalog)

    # Grid size distribution (bucketed by max dimension)
    size_buckets: dict[str, int] = Counter()
    for t in catalog:
        s = max(t["grid_size"]["rows"], t["grid_size"]["cols"])
        if s <= 2:
            size_buckets["2x2"] += 1
        elif s <= 3:
            size_buckets["3x3"] += 1
        elif s <= 4:
            size_buckets["4x4"] += 1
        elif s <= 5:
            size_buckets["5x5"] += 1
        elif s <= 6:
            size_buckets["6x6"] += 1
        elif s <= 8:
            size_buckets["7x7-8x8"] += 1
        else:
            size_buckets["9x9-10x10"] += 1

    return {
        "total_tasks": len(catalog),
        "transform_types": len(TRANSFORM_TYPES),
        "transform_distribution": dict(sorted(transform_dist.items())),
        "grid_size_distribution": {
            k: size_buckets.get(k, 0)
            for k in ["2x2", "3x3", "4x4", "5x5", "6x6", "7x7-8x8", "9x9-10x10"]
        },
        "base_seed": _CATALOG_BASE_SEED,
        "catalog_count": _CATALOG_COUNT,
    }


@router.get("")
async def list_tasks(
    count: int = Query(default=100, ge=1, le=1000, description="Number of tasks to return"),
    offset: int = Query(default=0, ge=0, description="Offset into the catalog"),
    transform_type: str | None = Query(default=None, description="Filter by transform type"),
):
    """List generated tasks with pagination and optional transform filter.

    Returns summary entries (no full grid payloads) for efficiency.
    Use GET /tasks/{task_id} for the full payload.
    """
    catalog = _get_catalog()

    # Optional filter
    if transform_type is not None:
        if transform_type not in TRANSFORM_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown transform_type '{transform_type}'. "
                       f"Valid types: {TRANSFORM_TYPES}",
            )
        filtered = [t for t in catalog if t["transform_type"] == transform_type]
    else:
        filtered = catalog

    # Paginate
    total = len(filtered)
    page = filtered[offset : offset + count]

    # Return summaries (no grids — those are big)
    summaries = [
        {
            "task_id": t["task_id"],
            "description": t["description"],
            "transform_type": t["transform_type"],
            "grid_size": t["grid_size"],
            "seed": t["seed"],
        }
        for t in page
    ]

    return {
        "tasks": summaries,
        "total": total,
        "count": len(summaries),
        "offset": offset,
    }


@router.get("/{task_id}")
async def get_task(task_id: str):
    """Get a specific generated task with full payload (input_grid + expected_output)."""
    index = _get_index()
    task = index.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found")
    return task
