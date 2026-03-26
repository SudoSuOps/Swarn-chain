"""Procedural ARC task generator — deterministic grid transformations from seeds.

Each seed maps to exactly one task via a pure function chain:
  seed -> RNG -> grid + transform_type -> input_grid + expected_output

25 transform types cover geometric, color, pooling, and gravity operations.
All transforms are pure functions: input_grid -> output_grid.
"""
from __future__ import annotations

import random
from collections import Counter, deque
from typing import Any

# ARC color palette: 0=black, 1=blue, 2=red, 3=green, 4=yellow,
#                    5=gray, 6=magenta, 7=orange, 8=cyan, 9=maroon
MAX_COLOR = 9

# Ordered list of all 25 transform types
TRANSFORM_TYPES: list[str] = [
    "mirror_h",
    "mirror_v",
    "rotate_90",
    "rotate_180",
    "rotate_270",
    "transpose",
    "color_swap",
    "invert",
    "fill_zeros",
    "scale_2x",
    "border_add",
    "crop_1",
    "shift_right",
    "shift_down",
    "shift_left",
    "shift_up",
    "gravity_down",
    "gravity_left",
    "flood_fill",
    "pattern_tile_2x2",
    "checkerboard",
    "diagonal_mirror",
    "color_remap",
    "max_pool_2x2",
    "sort_rows",
]

# Transforms that need a minimum grid size to produce valid output
_MIN_SIZE_FOR_TRANSFORM: dict[str, int] = {
    "crop_1": 3,         # need at least 3x3 to crop to 1x1
    "max_pool_2x2": 2,   # need at least 2x2 for pooling
}

# Grid size bucket weights — we pick a "max dimension" bucket first,
# then sample rows and cols uniformly within that bucket.
# Target: 2x2~50, 3x3~200, 4x4~250, 5x5~200, 6x6~150, 7-8~100, 9-10~50
_GRID_BUCKET_WEIGHTS: list[tuple[int, float]] = [
    (2, 50.0),
    (3, 200.0),
    (4, 250.0),
    (5, 200.0),
    (6, 150.0),
    (7, 50.0),
    (8, 50.0),
    (9, 25.0),
    (10, 25.0),
]


Grid = list[list[int]]


# ---------------------------------------------------------------------------
# 25 Transform implementations — each is a pure function
# ---------------------------------------------------------------------------


def _mirror_h(grid: Grid, rng: random.Random) -> Grid:
    """Flip horizontally (reverse each row)."""
    return [row[::-1] for row in grid]


def _mirror_v(grid: Grid, rng: random.Random) -> Grid:
    """Flip vertically (reverse row order)."""
    return grid[::-1]


def _rotate_90(grid: Grid, rng: random.Random) -> Grid:
    """Rotate 90 degrees clockwise."""
    rows, cols = len(grid), len(grid[0])
    return [[grid[rows - 1 - r][c] for r in range(rows)] for c in range(cols)]


def _rotate_180(grid: Grid, rng: random.Random) -> Grid:
    """Rotate 180 degrees."""
    return [row[::-1] for row in grid[::-1]]


def _rotate_270(grid: Grid, rng: random.Random) -> Grid:
    """Rotate 270 degrees clockwise (= 90 counter-clockwise)."""
    rows, cols = len(grid), len(grid[0])
    return [[grid[r][cols - 1 - c] for r in range(rows)] for c in range(cols)]


def _transpose(grid: Grid, rng: random.Random) -> Grid:
    """Swap rows and columns."""
    rows, cols = len(grid), len(grid[0])
    return [[grid[r][c] for r in range(rows)] for c in range(cols)]


def _color_swap(grid: Grid, rng: random.Random) -> Grid:
    """Swap two specific colors determined by the RNG."""
    # Collect all distinct colors in the grid
    colors_present = set()
    for row in grid:
        for v in row:
            colors_present.add(v)

    colors_list = sorted(colors_present)
    if len(colors_list) < 2:
        # Not enough colors — swap color with a new one
        c1 = colors_list[0]
        c2 = (c1 + 1) % (MAX_COLOR + 1)
    else:
        pair = rng.sample(colors_list, 2)
        c1, c2 = pair[0], pair[1]

    return [[c2 if v == c1 else c1 if v == c2 else v for v in row] for row in grid]


def _invert(grid: Grid, rng: random.Random) -> Grid:
    """0 -> 1, nonzero -> 0."""
    return [[1 if v == 0 else 0 for v in row] for row in grid]


def _fill_zeros(grid: Grid, rng: random.Random) -> Grid:
    """Replace all 0s with a seed-derived color (1-9)."""
    fill_color = rng.randint(1, MAX_COLOR)
    return [[fill_color if v == 0 else v for v in row] for row in grid]


def _scale_2x(grid: Grid, rng: random.Random) -> Grid:
    """Each cell becomes a 2x2 block — output is 2x the dimensions."""
    result = []
    for row in grid:
        expanded_row = []
        for v in row:
            expanded_row.extend([v, v])
        result.append(expanded_row)
        result.append(list(expanded_row))  # duplicate row
    return result


def _border_add(grid: Grid, rng: random.Random) -> Grid:
    """Add a 1-cell border of a seed-derived color."""
    border_color = rng.randint(1, MAX_COLOR)
    rows, cols = len(grid), len(grid[0])
    new_cols = cols + 2
    result = [[border_color] * new_cols]  # top border
    for row in grid:
        result.append([border_color] + row + [border_color])
    result.append([border_color] * new_cols)  # bottom border
    return result


def _crop_1(grid: Grid, rng: random.Random) -> Grid:
    """Remove outermost row/col on all sides."""
    rows, cols = len(grid), len(grid[0])
    # Guaranteed rows >= 3 and cols >= 3 by min-size enforcement
    return [row[1:-1] for row in grid[1:-1]]


def _shift_right(grid: Grid, rng: random.Random) -> Grid:
    """Shift all cells right by 1, wrapping."""
    return [row[-1:] + row[:-1] for row in grid]


def _shift_down(grid: Grid, rng: random.Random) -> Grid:
    """Shift all rows down by 1, wrapping."""
    return grid[-1:] + grid[:-1]


def _shift_left(grid: Grid, rng: random.Random) -> Grid:
    """Shift all cells left by 1, wrapping."""
    return [row[1:] + row[:1] for row in grid]


def _shift_up(grid: Grid, rng: random.Random) -> Grid:
    """Shift all rows up by 1, wrapping."""
    return grid[1:] + grid[:1]


def _gravity_down(grid: Grid, rng: random.Random) -> Grid:
    """Non-zero cells fall to the bottom of each column."""
    rows, cols = len(grid), len(grid[0])
    result = [[0] * cols for _ in range(rows)]
    for c in range(cols):
        non_zero = [grid[r][c] for r in range(rows) if grid[r][c] != 0]
        # Pack non-zero values to the bottom
        start = rows - len(non_zero)
        for i, v in enumerate(non_zero):
            result[start + i][c] = v
    return result


def _gravity_left(grid: Grid, rng: random.Random) -> Grid:
    """Non-zero cells fall to the left of each row."""
    result = []
    for row in grid:
        non_zero = [v for v in row if v != 0]
        padded = non_zero + [0] * (len(row) - len(non_zero))
        result.append(padded)
    return result


def _flood_fill(grid: Grid, rng: random.Random) -> Grid:
    """BFS flood fill from the top-left 0-region with a seed-derived color."""
    fill_color = rng.randint(1, MAX_COLOR)
    rows, cols = len(grid), len(grid[0])
    result = [list(row) for row in grid]

    # Find target color at (0, 0)
    target = result[0][0]
    if target == fill_color:
        # If top-left already matches fill color, pick a different one
        fill_color = (fill_color % MAX_COLOR) + 1

    if target != 0:
        # Only flood fill if the origin is 0
        # If origin is nonzero, find the first 0-cell via BFS and start there
        found = False
        for r in range(rows):
            for c in range(cols):
                if result[r][c] == 0:
                    target = 0
                    start_r, start_c = r, c
                    found = True
                    break
            if found:
                break
        if not found:
            # No zeros in grid — just return as-is
            return result
    else:
        start_r, start_c = 0, 0

    # BFS fill
    visited = set()
    queue = deque([(start_r, start_c)])
    visited.add((start_r, start_c))

    while queue:
        r, c = queue.popleft()
        result[r][c] = fill_color
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols and (nr, nc) not in visited and result[nr][nc] == target:
                visited.add((nr, nc))
                queue.append((nr, nc))

    return result


def _pattern_tile_2x2(grid: Grid, rng: random.Random) -> Grid:
    """Tile the grid into a 2x larger grid (2x2 copies)."""
    rows, cols = len(grid), len(grid[0])
    result = []
    for _ in range(2):
        for row in grid:
            result.append(row + row)
    return result


def _checkerboard(grid: Grid, rng: random.Random) -> Grid:
    """Replace grid with checkerboard using the two most common colors."""
    # Count colors
    counter: Counter[int] = Counter()
    for row in grid:
        for v in row:
            counter[v] += 1

    most_common = counter.most_common()
    c1 = most_common[0][0]
    c2 = most_common[1][0] if len(most_common) > 1 else (c1 + 1) % (MAX_COLOR + 1)

    rows, cols = len(grid), len(grid[0])
    return [[(c1 if (r + c) % 2 == 0 else c2) for c in range(cols)] for r in range(rows)]


def _diagonal_mirror(grid: Grid, rng: random.Random) -> Grid:
    """Mirror across main diagonal (same as transpose)."""
    rows, cols = len(grid), len(grid[0])
    return [[grid[r][c] for r in range(rows)] for c in range(cols)]


def _color_remap(grid: Grid, rng: random.Random) -> Grid:
    """Remap colors based on a seed-derived permutation."""
    # Build a mapping from each present color to another
    colors_present = set()
    for row in grid:
        for v in row:
            colors_present.add(v)

    colors_list = sorted(colors_present)
    shuffled = list(colors_list)
    rng.shuffle(shuffled)

    # Ensure at least one color actually changes (avoid identity map)
    if shuffled == colors_list and len(colors_list) > 1:
        shuffled[0], shuffled[1] = shuffled[1], shuffled[0]

    mapping = dict(zip(colors_list, shuffled))
    return [[mapping[v] for v in row] for row in grid]


def _max_pool_2x2(grid: Grid, rng: random.Random) -> Grid:
    """2x2 max pooling — reduce grid by half, take max in each 2x2 block."""
    rows, cols = len(grid), len(grid[0])
    # Truncate to even dimensions
    pool_rows = rows // 2
    pool_cols = cols // 2
    result = []
    for r in range(pool_rows):
        result_row = []
        for c in range(pool_cols):
            block = [
                grid[2 * r][2 * c],
                grid[2 * r][2 * c + 1],
                grid[2 * r + 1][2 * c],
                grid[2 * r + 1][2 * c + 1],
            ]
            result_row.append(max(block))
        result.append(result_row)
    return result


def _sort_rows(grid: Grid, rng: random.Random) -> Grid:
    """Sort each row in ascending order."""
    return [sorted(row) for row in grid]


# ---------------------------------------------------------------------------
# Transform dispatch table
# ---------------------------------------------------------------------------

_TRANSFORM_FN: dict[str, Any] = {
    "mirror_h": _mirror_h,
    "mirror_v": _mirror_v,
    "rotate_90": _rotate_90,
    "rotate_180": _rotate_180,
    "rotate_270": _rotate_270,
    "transpose": _transpose,
    "color_swap": _color_swap,
    "invert": _invert,
    "fill_zeros": _fill_zeros,
    "scale_2x": _scale_2x,
    "border_add": _border_add,
    "crop_1": _crop_1,
    "shift_right": _shift_right,
    "shift_down": _shift_down,
    "shift_left": _shift_left,
    "shift_up": _shift_up,
    "gravity_down": _gravity_down,
    "gravity_left": _gravity_left,
    "flood_fill": _flood_fill,
    "pattern_tile_2x2": _pattern_tile_2x2,
    "checkerboard": _checkerboard,
    "diagonal_mirror": _diagonal_mirror,
    "color_remap": _color_remap,
    "max_pool_2x2": _max_pool_2x2,
    "sort_rows": _sort_rows,
}

# Verify all 25 transforms are registered
assert len(_TRANSFORM_FN) == 25, f"Expected 25 transforms, got {len(_TRANSFORM_FN)}"
assert set(_TRANSFORM_FN.keys()) == set(TRANSFORM_TYPES)

# Human-readable descriptions for each transform
_TRANSFORM_DESCRIPTIONS: dict[str, str] = {
    "mirror_h": "Flip the grid horizontally (reverse each row)",
    "mirror_v": "Flip the grid vertically (reverse row order)",
    "rotate_90": "Rotate the grid 90 degrees clockwise",
    "rotate_180": "Rotate the grid 180 degrees",
    "rotate_270": "Rotate the grid 270 degrees clockwise",
    "transpose": "Transpose the grid (swap rows and columns)",
    "color_swap": "Swap two specific colors in the grid",
    "invert": "Invert the grid: 0 becomes 1, nonzero becomes 0",
    "fill_zeros": "Replace all zeros with a specific color",
    "scale_2x": "Scale the grid 2x (each cell becomes a 2x2 block)",
    "border_add": "Add a 1-cell border around the grid",
    "crop_1": "Remove the outermost row and column on all sides",
    "shift_right": "Shift all cells right by 1, wrapping around",
    "shift_down": "Shift all rows down by 1, wrapping around",
    "shift_left": "Shift all cells left by 1, wrapping around",
    "shift_up": "Shift all rows up by 1, wrapping around",
    "gravity_down": "Non-zero cells fall to the bottom of each column",
    "gravity_left": "Non-zero cells fall to the left of each row",
    "flood_fill": "BFS flood fill from the first 0-region with a color",
    "pattern_tile_2x2": "Tile the grid into a 2x larger grid (2x2 copies)",
    "checkerboard": "Replace with checkerboard using the two most common colors",
    "diagonal_mirror": "Mirror across the main diagonal",
    "color_remap": "Remap all colors based on a seed-derived permutation",
    "max_pool_2x2": "2x2 max pooling (reduce grid by half, take max in each block)",
    "sort_rows": "Sort each row in ascending order",
}


# ---------------------------------------------------------------------------
# Grid generation helpers
# ---------------------------------------------------------------------------


def _pick_grid_size(rng: random.Random, transform_type: str) -> tuple[int, int]:
    """Pick (rows, cols) with a bucket-first strategy for correct distribution.

    Strategy: pick a max-dimension bucket, then sample rows and cols so that
    max(rows, cols) == bucket value. This gives precise control over the
    grid-size distribution as perceived by the caller.
    """
    min_size = _MIN_SIZE_FOR_TRANSFORM.get(transform_type, 2)

    # Filter buckets by min size
    valid = [(s, w) for s, w in _GRID_BUCKET_WEIGHTS if s >= min_size]
    if not valid:
        valid = [(min_size, 1.0)]

    # For max_pool_2x2, restrict to even bucket sizes
    if transform_type == "max_pool_2x2":
        even_valid = [(s, w) for s, w in valid if s % 2 == 0]
        if even_valid:
            valid = even_valid
        else:
            valid = [(2, 1.0)]

    bucket_sizes = [s for s, _ in valid]
    bucket_weights = [w for _, w in valid]

    max_dim = rng.choices(bucket_sizes, weights=bucket_weights, k=1)[0]

    # Sample rows and cols such that max(rows, cols) == max_dim
    # One axis gets max_dim, the other gets a random value in [min_size, max_dim]
    lo = max(min_size, 2)
    other_dim = rng.randint(lo, max_dim)

    if transform_type == "max_pool_2x2":
        # Force both even
        other_dim = other_dim if other_dim % 2 == 0 else other_dim + 1
        if other_dim > max_dim:
            other_dim = max_dim

    # Randomly assign which axis gets the max
    if rng.random() < 0.5:
        rows, cols = max_dim, other_dim
    else:
        rows, cols = other_dim, max_dim

    return rows, cols


def _generate_grid(rng: random.Random, rows: int, cols: int, num_colors: int) -> Grid:
    """Generate a random grid with the given dimensions and color count."""
    # Pick which colors to use (always include 0 as one of them for variety)
    if num_colors <= 1:
        palette = [0]
    else:
        # Always include 0, pick the rest from 1-9
        other_colors = rng.sample(range(1, MAX_COLOR + 1), min(num_colors - 1, MAX_COLOR))
        palette = [0] + other_colors

    return [[rng.choice(palette) for _ in range(cols)] for _ in range(rows)]


# ---------------------------------------------------------------------------
# Main generator class
# ---------------------------------------------------------------------------


class ARCTaskGenerator:
    """Deterministic procedural ARC task generator.

    Each seed maps to exactly one task. The same seed always produces the same
    task. The catalog of 1000 tasks is a fixed, reproducible dataset.
    """

    def generate(self, seed: int) -> dict:
        """Generate one ARC task deterministically from a seed.

        Returns:
            dict with keys: task_id, description, input_grid, expected_output,
                            transform_type, grid_size, seed
        """
        rng = random.Random(seed)

        # 1. Pick transform type (uniform across all 25)
        transform_type = TRANSFORM_TYPES[seed % len(TRANSFORM_TYPES)]

        # 2. Pick grid size
        rows, cols = _pick_grid_size(rng, transform_type)

        # 3. Pick number of colors (2-5)
        num_colors = rng.randint(2, 5)

        # 4. Generate input grid
        input_grid = _generate_grid(rng, rows, cols, num_colors)

        # 5. Apply transform to get expected output
        # Create a fresh RNG fork for the transform (so transform params are deterministic)
        transform_rng = random.Random(rng.randint(0, 2**32 - 1))
        transform_fn = _TRANSFORM_FN[transform_type]
        expected_output = transform_fn(input_grid, transform_rng)

        # 6. Compute output grid size
        out_rows = len(expected_output)
        out_cols = len(expected_output[0]) if out_rows > 0 else 0

        # 7. Build task ID
        task_id = f"arc-gen-{seed:05d}-{transform_type}"

        # 8. Build description
        base_desc = _TRANSFORM_DESCRIPTIONS[transform_type]
        description = f"{base_desc} ({rows}x{cols} -> {out_rows}x{out_cols})"

        return {
            "task_id": task_id,
            "description": description,
            "input_grid": input_grid,
            "expected_output": expected_output,
            "transform_type": transform_type,
            "grid_size": {"rows": rows, "cols": cols},
            "seed": seed,
        }

    def generate_catalog(self, count: int = 1000, base_seed: int = 42) -> list[dict]:
        """Generate a catalog of `count` tasks starting from `base_seed`.

        Seeds used: base_seed, base_seed+1, ..., base_seed+count-1
        """
        return [self.generate(base_seed + i) for i in range(count)]
