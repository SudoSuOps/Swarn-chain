"""Tests for ARCVerifier — deterministic scoring is the anchor of integrity."""
import pytest
from swarmchain.services.verifier import ARCVerifier


@pytest.fixture
def verifier() -> ARCVerifier:
    return ARCVerifier()


@pytest.fixture
def task_payload() -> dict:
    return {
        "expected_output": [
            [1, 1, 1],
            [1, 2, 1],
            [1, 1, 1],
        ],
    }


class TestARCVerifierExactMatch:
    """Exact match should score 1.0."""

    def test_exact_match_returns_perfect_score(self, verifier: ARCVerifier, task_payload: dict):
        attempt = {
            "grid": [
                [1, 1, 1],
                [1, 2, 1],
                [1, 1, 1],
            ]
        }
        result = verifier.verify(task_payload, attempt)
        assert result["score"] == 1.0
        assert result["valid"] is True
        assert result["details"]["exact_match"] is True
        assert result["details"]["correct_cells"] == 9
        assert result["details"]["wrong_cells_count"] == 0


class TestARCVerifierPartialMatch:
    """Partial match should return the proportion of correct cells."""

    def test_one_wrong_cell(self, verifier: ARCVerifier, task_payload: dict):
        attempt = {
            "grid": [
                [1, 1, 1],
                [1, 2, 1],
                [1, 1, 0],  # last cell wrong
            ]
        }
        result = verifier.verify(task_payload, attempt)
        assert result["score"] == pytest.approx(8.0 / 9.0)
        assert result["valid"] is True
        assert result["details"]["exact_match"] is False
        assert result["details"]["correct_cells"] == 8
        assert result["details"]["wrong_cells_count"] == 1

    def test_half_correct(self, verifier: ARCVerifier, task_payload: dict):
        # 5 of 9 cells wrong => 4 correct
        attempt = {
            "grid": [
                [0, 0, 0],
                [0, 2, 0],
                [1, 1, 1],
            ]
        }
        result = verifier.verify(task_payload, attempt)
        # Row 0: all wrong (3 wrong), Row 1: middle correct (2 wrong), Row 2: all correct
        # Correct: row1-col1(2), row2-col0(1), row2-col1(1), row2-col2(1) = 4
        assert result["score"] == pytest.approx(4.0 / 9.0)
        assert result["valid"] is True

    def test_all_wrong(self, verifier: ARCVerifier, task_payload: dict):
        attempt = {
            "grid": [
                [0, 0, 0],
                [0, 0, 0],
                [0, 0, 0],
            ]
        }
        result = verifier.verify(task_payload, attempt)
        # Only cell [1][1] expected 2, submitted 0 -> wrong. All cells wrong.
        assert result["score"] == pytest.approx(0.0)
        assert result["valid"] is True
        assert result["details"]["correct_cells"] == 0


class TestARCVerifierWrongDimensions:
    """Wrong grid dimensions should score 0.0."""

    def test_too_few_rows(self, verifier: ARCVerifier, task_payload: dict):
        attempt = {
            "grid": [
                [1, 1, 1],
                [1, 2, 1],
            ]
        }
        result = verifier.verify(task_payload, attempt)
        assert result["score"] == 0.0
        assert result["valid"] is False
        assert "dimension mismatch" in result["details"]["error"]

    def test_too_many_rows(self, verifier: ARCVerifier, task_payload: dict):
        attempt = {
            "grid": [
                [1, 1, 1],
                [1, 2, 1],
                [1, 1, 1],
                [1, 1, 1],
            ]
        }
        result = verifier.verify(task_payload, attempt)
        assert result["score"] == 0.0
        assert result["valid"] is False

    def test_wrong_columns(self, verifier: ARCVerifier, task_payload: dict):
        attempt = {
            "grid": [
                [1, 1],
                [1, 2],
                [1, 1],
            ]
        }
        result = verifier.verify(task_payload, attempt)
        assert result["score"] == 0.0
        assert result["valid"] is False


class TestARCVerifierMissingGrid:
    """Missing grid in attempt should score 0.0."""

    def test_no_grid_key(self, verifier: ARCVerifier, task_payload: dict):
        attempt = {"answer": "some text"}
        result = verifier.verify(task_payload, attempt)
        assert result["score"] == 0.0
        assert result["valid"] is False
        assert "no grid" in result["details"]["error"]

    def test_empty_attempt(self, verifier: ARCVerifier, task_payload: dict):
        attempt = {}
        result = verifier.verify(task_payload, attempt)
        assert result["score"] == 0.0
        assert result["valid"] is False

    def test_grid_is_none(self, verifier: ARCVerifier, task_payload: dict):
        attempt = {"grid": None}
        result = verifier.verify(task_payload, attempt)
        assert result["score"] == 0.0
        assert result["valid"] is False

    def test_no_expected_output(self, verifier: ARCVerifier):
        task = {"input_grid": [[1, 2], [3, 4]]}
        attempt = {"grid": [[1, 2], [3, 4]]}
        result = verifier.verify(task, attempt)
        assert result["score"] == 0.0
        assert result["valid"] is False
        assert "no expected_output" in result["details"]["error"]


class TestARCVerifierEmptyGrid:
    """Empty grid should score 0.0."""

    def test_empty_expected_and_submitted(self, verifier: ARCVerifier):
        task = {"expected_output": []}
        attempt = {"grid": []}
        result = verifier.verify(task, attempt)
        assert result["score"] == 0.0
        assert result["valid"] is False

    def test_grid_is_string_not_list(self, verifier: ARCVerifier, task_payload: dict):
        attempt = {"grid": "not a grid"}
        result = verifier.verify(task_payload, attempt)
        assert result["score"] == 0.0
        assert result["valid"] is False
