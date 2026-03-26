"""Tests for the procedural ARC task generator — 25 transforms, 1000-block pipeline.

Covers:
  - Each of the 25 transforms produces valid output for multiple seeds
  - Catalog of 1000 tasks is complete, unique, and deterministic
  - All tasks have valid grids and pass the ARC verifier at 1.0
  - Grid size distribution is roughly correct
  - API endpoints return correct data
"""
import pytest
import pytest_asyncio
from collections import Counter

from swarmchain.tasks.arc_generator import (
    ARCTaskGenerator,
    TRANSFORM_TYPES,
    _TRANSFORM_FN,
    Grid,
)
from swarmchain.services.verifier import ARCVerifier


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def generator() -> ARCTaskGenerator:
    return ARCTaskGenerator()


@pytest.fixture
def verifier() -> ARCVerifier:
    return ARCVerifier()


@pytest.fixture
def catalog(generator: ARCTaskGenerator) -> list[dict]:
    """Full 1000-task catalog — cached per test session via fixture."""
    return generator.generate_catalog(1000)


# ---------------------------------------------------------------------------
# Transform correctness — each of 25 transforms, 5 seeds each
# ---------------------------------------------------------------------------

class TestAllTransforms:
    """Every transform must produce a non-empty, valid grid for multiple seeds."""

    @pytest.mark.parametrize("transform_type", TRANSFORM_TYPES)
    def test_transform_produces_valid_output(self, generator: ARCTaskGenerator, transform_type: str):
        """Each transform produces valid grids for 5 different seeds."""
        # Use seeds that map to this specific transform
        idx = TRANSFORM_TYPES.index(transform_type)
        test_seeds = [idx + i * 25 for i in range(5)]  # 5 seeds per transform

        for seed in test_seeds:
            task = generator.generate(seed)
            assert task["transform_type"] == transform_type, (
                f"Seed {seed} should produce {transform_type}, got {task['transform_type']}"
            )

            # Validate input grid
            inp = task["input_grid"]
            assert isinstance(inp, list) and len(inp) > 0
            inp_cols = len(inp[0])
            assert inp_cols > 0
            for row in inp:
                assert len(row) == inp_cols, "Ragged input grid"
                for v in row:
                    assert isinstance(v, int) and 0 <= v <= 9

            # Validate output grid
            out = task["expected_output"]
            assert isinstance(out, list) and len(out) > 0
            out_cols = len(out[0])
            assert out_cols > 0
            for row in out:
                assert len(row) == out_cols, "Ragged output grid"
                for v in row:
                    assert isinstance(v, int) and 0 <= v <= 9

    @pytest.mark.parametrize("transform_type", TRANSFORM_TYPES)
    def test_transform_is_registered(self, transform_type: str):
        """All transform types have a function in the dispatch table."""
        assert transform_type in _TRANSFORM_FN


class TestTransformDimensionChanges:
    """Transforms that change grid dimensions produce correct output sizes."""

    def test_scale_2x_doubles_dimensions(self, generator: ARCTaskGenerator):
        task = generator.generate(TRANSFORM_TYPES.index("scale_2x"))
        rows, cols = task["grid_size"]["rows"], task["grid_size"]["cols"]
        out = task["expected_output"]
        assert len(out) == rows * 2
        assert len(out[0]) == cols * 2

    def test_border_add_increases_by_2(self, generator: ARCTaskGenerator):
        task = generator.generate(TRANSFORM_TYPES.index("border_add"))
        rows, cols = task["grid_size"]["rows"], task["grid_size"]["cols"]
        out = task["expected_output"]
        assert len(out) == rows + 2
        assert len(out[0]) == cols + 2

    def test_crop_1_decreases_by_2(self, generator: ARCTaskGenerator):
        task = generator.generate(TRANSFORM_TYPES.index("crop_1"))
        rows, cols = task["grid_size"]["rows"], task["grid_size"]["cols"]
        out = task["expected_output"]
        assert len(out) == rows - 2
        assert len(out[0]) == cols - 2

    def test_pattern_tile_2x2_doubles(self, generator: ARCTaskGenerator):
        task = generator.generate(TRANSFORM_TYPES.index("pattern_tile_2x2"))
        rows, cols = task["grid_size"]["rows"], task["grid_size"]["cols"]
        out = task["expected_output"]
        assert len(out) == rows * 2
        assert len(out[0]) == cols * 2

    def test_max_pool_2x2_halves(self, generator: ARCTaskGenerator):
        task = generator.generate(TRANSFORM_TYPES.index("max_pool_2x2"))
        rows, cols = task["grid_size"]["rows"], task["grid_size"]["cols"]
        out = task["expected_output"]
        assert len(out) == rows // 2
        assert len(out[0]) == cols // 2

    def test_transpose_swaps_dimensions(self, generator: ARCTaskGenerator):
        task = generator.generate(TRANSFORM_TYPES.index("transpose"))
        rows, cols = task["grid_size"]["rows"], task["grid_size"]["cols"]
        out = task["expected_output"]
        assert len(out) == cols
        assert len(out[0]) == rows

    def test_rotate_90_swaps_dimensions(self, generator: ARCTaskGenerator):
        task = generator.generate(TRANSFORM_TYPES.index("rotate_90"))
        rows, cols = task["grid_size"]["rows"], task["grid_size"]["cols"]
        out = task["expected_output"]
        assert len(out) == cols
        assert len(out[0]) == rows


# ---------------------------------------------------------------------------
# Catalog-level tests
# ---------------------------------------------------------------------------

class TestCatalog:
    """The 1000-task catalog must be complete, unique, and well-distributed."""

    def test_catalog_has_1000_tasks(self, catalog: list[dict]):
        assert len(catalog) == 1000

    def test_all_task_ids_are_unique(self, catalog: list[dict]):
        ids = [t["task_id"] for t in catalog]
        assert len(set(ids)) == 1000

    def test_task_id_format(self, catalog: list[dict]):
        """Task IDs follow the arc-gen-XXXXX-transform pattern."""
        import re
        pattern = re.compile(r"^arc-gen-\d{5}-.+$")
        for t in catalog:
            assert pattern.match(t["task_id"]), f"Bad task_id: {t['task_id']}"

    def test_all_25_transforms_represented(self, catalog: list[dict]):
        """Every transform type appears in the catalog."""
        types_seen = set(t["transform_type"] for t in catalog)
        assert types_seen == set(TRANSFORM_TYPES)

    def test_uniform_transform_distribution(self, catalog: list[dict]):
        """Each transform gets exactly 40 tasks (1000 / 25)."""
        dist = Counter(t["transform_type"] for t in catalog)
        for tt in TRANSFORM_TYPES:
            assert dist[tt] == 40, f"{tt} has {dist[tt]} tasks, expected 40"

    def test_grid_size_distribution(self, catalog: list[dict]):
        """Grid size distribution is roughly correct (within tolerance)."""
        size_buckets: Counter = Counter()
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

        # Target: 2x2~50, 3x3~200, 4x4~250, 5x5~200, 6x6~150, 7-8~100, 9-10~50
        # Allow generous tolerance because of RNG variance
        targets = {
            "2x2": (10, 120),
            "3x3": (100, 350),
            "4x4": (150, 400),
            "5x5": (100, 350),
            "6x6": (50, 300),
            "7x7-8x8": (30, 200),
            "9x9-10x10": (10, 120),
        }
        for bucket, (lo, hi) in targets.items():
            actual = size_buckets.get(bucket, 0)
            assert lo <= actual <= hi, (
                f"Bucket {bucket}: {actual} tasks, expected {lo}-{hi}"
            )

    def test_all_tasks_have_required_keys(self, catalog: list[dict]):
        required = {"task_id", "description", "input_grid", "expected_output",
                     "transform_type", "grid_size", "seed"}
        for t in catalog:
            assert required.issubset(t.keys()), f"Missing keys in {t['task_id']}"


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------

class TestDeterminism:
    """Same seed must always produce the exact same task."""

    def test_same_seed_same_task(self, generator: ARCTaskGenerator):
        for seed in [0, 42, 100, 500, 999]:
            t1 = generator.generate(seed)
            t2 = generator.generate(seed)
            assert t1 == t2, f"Seed {seed} produced different results on second call"

    def test_different_seeds_different_tasks(self, generator: ARCTaskGenerator):
        t1 = generator.generate(42)
        t2 = generator.generate(43)
        assert t1["task_id"] != t2["task_id"]

    def test_catalog_is_deterministic(self, generator: ARCTaskGenerator):
        c1 = generator.generate_catalog(100, base_seed=0)
        c2 = generator.generate_catalog(100, base_seed=0)
        for a, b in zip(c1, c2):
            assert a == b


# ---------------------------------------------------------------------------
# Verifier integration
# ---------------------------------------------------------------------------

class TestVerifierIntegration:
    """Every generated task's expected_output scores 1.0 against itself."""

    def test_all_1000_tasks_self_verify(self, catalog: list[dict], verifier: ARCVerifier):
        for t in catalog:
            result = verifier.verify(
                {"expected_output": t["expected_output"]},
                {"grid": t["expected_output"]},
            )
            assert result["score"] == 1.0, (
                f"Task {t['task_id']} self-verify failed: score={result['score']}"
            )
            assert result["valid"] is True
            assert result["details"]["exact_match"] is True

    @pytest.mark.parametrize("transform_type", TRANSFORM_TYPES)
    def test_verifier_per_transform(self, generator: ARCTaskGenerator, verifier: ARCVerifier, transform_type: str):
        """Spot-check 3 seeds per transform through the verifier."""
        idx = TRANSFORM_TYPES.index(transform_type)
        for i in range(3):
            seed = idx + i * 25
            task = generator.generate(seed)
            result = verifier.verify(
                {"expected_output": task["expected_output"]},
                {"grid": task["expected_output"]},
            )
            assert result["score"] == 1.0


# ---------------------------------------------------------------------------
# Specific transform behavior tests
# ---------------------------------------------------------------------------

class TestSpecificTransforms:
    """Verify correctness of specific transforms against hand-computed results."""

    def test_mirror_h(self):
        from swarmchain.tasks.arc_generator import _mirror_h
        import random
        grid = [[1, 2, 3], [4, 5, 6]]
        result = _mirror_h(grid, random.Random(0))
        assert result == [[3, 2, 1], [6, 5, 4]]

    def test_mirror_v(self):
        from swarmchain.tasks.arc_generator import _mirror_v
        import random
        grid = [[1, 2], [3, 4], [5, 6]]
        result = _mirror_v(grid, random.Random(0))
        assert result == [[5, 6], [3, 4], [1, 2]]

    def test_rotate_90(self):
        from swarmchain.tasks.arc_generator import _rotate_90
        import random
        grid = [[1, 2], [3, 4]]
        result = _rotate_90(grid, random.Random(0))
        assert result == [[3, 1], [4, 2]]

    def test_rotate_180(self):
        from swarmchain.tasks.arc_generator import _rotate_180
        import random
        grid = [[1, 2], [3, 4]]
        result = _rotate_180(grid, random.Random(0))
        assert result == [[4, 3], [2, 1]]

    def test_rotate_270(self):
        from swarmchain.tasks.arc_generator import _rotate_270
        import random
        grid = [[1, 2], [3, 4]]
        result = _rotate_270(grid, random.Random(0))
        assert result == [[2, 4], [1, 3]]

    def test_transpose(self):
        from swarmchain.tasks.arc_generator import _transpose
        import random
        grid = [[1, 2, 3], [4, 5, 6]]
        result = _transpose(grid, random.Random(0))
        assert result == [[1, 4], [2, 5], [3, 6]]

    def test_invert(self):
        from swarmchain.tasks.arc_generator import _invert
        import random
        grid = [[0, 3, 0], [3, 0, 3]]
        result = _invert(grid, random.Random(0))
        assert result == [[1, 0, 1], [0, 1, 0]]

    def test_scale_2x(self):
        from swarmchain.tasks.arc_generator import _scale_2x
        import random
        grid = [[1, 2], [3, 4]]
        result = _scale_2x(grid, random.Random(0))
        assert result == [
            [1, 1, 2, 2],
            [1, 1, 2, 2],
            [3, 3, 4, 4],
            [3, 3, 4, 4],
        ]

    def test_sort_rows(self):
        from swarmchain.tasks.arc_generator import _sort_rows
        import random
        grid = [[3, 1, 2], [6, 4, 5]]
        result = _sort_rows(grid, random.Random(0))
        assert result == [[1, 2, 3], [4, 5, 6]]

    def test_gravity_down(self):
        from swarmchain.tasks.arc_generator import _gravity_down
        import random
        grid = [[1, 0], [0, 2], [0, 0]]
        result = _gravity_down(grid, random.Random(0))
        assert result == [[0, 0], [0, 0], [1, 2]]

    def test_gravity_left(self):
        from swarmchain.tasks.arc_generator import _gravity_left
        import random
        grid = [[0, 1, 0], [2, 0, 3]]
        result = _gravity_left(grid, random.Random(0))
        assert result == [[1, 0, 0], [2, 3, 0]]

    def test_shift_right(self):
        from swarmchain.tasks.arc_generator import _shift_right
        import random
        grid = [[1, 2, 3], [4, 5, 6]]
        result = _shift_right(grid, random.Random(0))
        assert result == [[3, 1, 2], [6, 4, 5]]

    def test_shift_left(self):
        from swarmchain.tasks.arc_generator import _shift_left
        import random
        grid = [[1, 2, 3], [4, 5, 6]]
        result = _shift_left(grid, random.Random(0))
        assert result == [[2, 3, 1], [5, 6, 4]]

    def test_shift_down(self):
        from swarmchain.tasks.arc_generator import _shift_down
        import random
        grid = [[1, 2], [3, 4], [5, 6]]
        result = _shift_down(grid, random.Random(0))
        assert result == [[5, 6], [1, 2], [3, 4]]

    def test_shift_up(self):
        from swarmchain.tasks.arc_generator import _shift_up
        import random
        grid = [[1, 2], [3, 4], [5, 6]]
        result = _shift_up(grid, random.Random(0))
        assert result == [[3, 4], [5, 6], [1, 2]]

    def test_max_pool_2x2(self):
        from swarmchain.tasks.arc_generator import _max_pool_2x2
        import random
        grid = [[1, 3], [2, 4]]
        result = _max_pool_2x2(grid, random.Random(0))
        assert result == [[4]]

    def test_max_pool_2x2_larger(self):
        from swarmchain.tasks.arc_generator import _max_pool_2x2
        import random
        grid = [[1, 3, 5, 7], [2, 4, 6, 8]]
        result = _max_pool_2x2(grid, random.Random(0))
        assert result == [[4, 8]]

    def test_checkerboard(self):
        from swarmchain.tasks.arc_generator import _checkerboard
        import random
        grid = [[1, 1, 2], [2, 1, 1]]
        result = _checkerboard(grid, random.Random(0))
        # Most common: 1 (4 times), second: 2 (2 times)
        assert result == [[1, 2, 1], [2, 1, 2]]

    def test_pattern_tile_2x2(self):
        from swarmchain.tasks.arc_generator import _pattern_tile_2x2
        import random
        grid = [[1, 2], [3, 4]]
        result = _pattern_tile_2x2(grid, random.Random(0))
        assert result == [
            [1, 2, 1, 2],
            [3, 4, 3, 4],
            [1, 2, 1, 2],
            [3, 4, 3, 4],
        ]

    def test_border_add(self):
        from swarmchain.tasks.arc_generator import _border_add
        import random
        rng = random.Random(42)
        grid = [[1, 2], [3, 4]]
        result = _border_add(grid, rng)
        # Border color is rng-derived
        bc = result[0][0]  # whatever the border color is
        assert len(result) == 4 and len(result[0]) == 4
        # Check corners and edges are border color
        assert result[0] == [bc, bc, bc, bc]
        assert result[3] == [bc, bc, bc, bc]
        assert result[1][0] == bc and result[1][3] == bc
        # Check interior preserved
        assert result[1][1] == 1 and result[1][2] == 2
        assert result[2][1] == 3 and result[2][2] == 4

    def test_crop_1(self):
        from swarmchain.tasks.arc_generator import _crop_1
        import random
        grid = [[9, 9, 9], [9, 5, 9], [9, 9, 9]]
        result = _crop_1(grid, random.Random(0))
        assert result == [[5]]

    def test_flood_fill_from_zero_origin(self):
        from swarmchain.tasks.arc_generator import _flood_fill
        import random
        rng = random.Random(42)
        grid = [[0, 0, 1], [0, 1, 1], [1, 1, 1]]
        result = _flood_fill(grid, rng)
        fill_color = result[0][0]
        assert fill_color != 0
        # The connected 0-region at top-left should be filled
        assert result[0][0] == fill_color
        assert result[0][1] == fill_color
        assert result[1][0] == fill_color
        # The 1s should remain
        assert result[0][2] == 1
        assert result[2][2] == 1


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------

class TestTasksAPI:
    """Test the /tasks endpoints via the test client."""

    @pytest.mark.asyncio
    async def test_list_tasks_default(self, test_client):
        resp = await test_client.get("/tasks")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1000
        assert data["count"] == 100  # default count
        assert data["offset"] == 0
        assert len(data["tasks"]) == 100

    @pytest.mark.asyncio
    async def test_list_tasks_pagination(self, test_client):
        resp = await test_client.get("/tasks?count=10&offset=990")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 10
        assert data["offset"] == 990

    @pytest.mark.asyncio
    async def test_list_tasks_filter_by_transform(self, test_client):
        resp = await test_client.get("/tasks?transform_type=mirror_h&count=1000")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 40
        for t in data["tasks"]:
            assert t["transform_type"] == "mirror_h"

    @pytest.mark.asyncio
    async def test_list_tasks_invalid_transform(self, test_client):
        resp = await test_client.get("/tasks?transform_type=nonexistent")
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_get_task_by_id(self, test_client):
        # First get a task ID from the list
        list_resp = await test_client.get("/tasks?count=1")
        task_id = list_resp.json()["tasks"][0]["task_id"]

        resp = await test_client.get(f"/tasks/{task_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["task_id"] == task_id
        assert "input_grid" in data
        assert "expected_output" in data
        assert "transform_type" in data

    @pytest.mark.asyncio
    async def test_get_task_not_found(self, test_client):
        resp = await test_client.get("/tasks/arc-gen-99999-nonexistent")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_stats_endpoint(self, test_client):
        resp = await test_client.get("/tasks/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_tasks"] == 1000
        assert data["transform_types"] == 25
        assert "transform_distribution" in data
        assert "grid_size_distribution" in data
        assert sum(data["transform_distribution"].values()) == 1000
        assert sum(data["grid_size_distribution"].values()) == 1000
