"""Tests for domain-routed finality validators.

Proves:
1. Validator interface works for all 3 domains
2. CRE Atlas produces correct decisions based on structural analysis
3. Validators cannot override objective verification (iron rule)
4. ValidatorRunner stores decisions and artifacts
5. API exposes validator decisions
"""
import pytest
from httpx import AsyncClient

# ─── Unit: CRE Atlas Validator ─────────────────────────────────


class TestCREAtlasValidator:
    """Test the CRE Atlas validator with various attempt structures."""

    @pytest.mark.asyncio
    async def test_complete_cre_attempt_approved(self):
        from swarmchain.services.domain_validators import CREAtlasValidator

        v = CREAtlasValidator()
        result = await v.validate_attempt(
            task_payload={},
            attempt_output={
                "property_type": "office",
                "location": "Manhattan, NY",
                "valuation": 15_000_000,
                "zoning": "C6-4",
                "financials": {"noi": 900_000, "expenses": 300_000},
                "comparables": [{"addr": "123 Main", "price": 14_000_000}],
                "risk_factors": ["tenant_concentration", "interest_rate_exposure"],
                "market_analysis": "Class A office, 94% occupied",
                "regulatory_notes": "Compliant with NYC zoning",
                "cap_rate": 0.06,
                "noi": 900_000,
            },
            objective_score=0.85,
        )
        assert result.verdict == "approved"
        assert result.confidence >= 0.8
        assert len(result.flags) == 0

    @pytest.mark.asyncio
    async def test_missing_required_sections_flagged(self):
        from swarmchain.services.domain_validators import CREAtlasValidator

        v = CREAtlasValidator()
        result = await v.validate_attempt(
            task_payload={},
            attempt_output={
                "property_type": "retail",
                # missing: location, valuation, zoning
            },
            objective_score=0.3,
        )
        assert result.verdict in ("flagged", "needs_review")
        assert result.confidence < 0.5
        assert any("missing_required:location" in f for f in result.flags)
        assert any("missing_required:valuation" in f for f in result.flags)
        assert any("missing_required:zoning" in f for f in result.flags)

    @pytest.mark.asyncio
    async def test_invalid_valuation_reduces_confidence(self):
        from swarmchain.services.domain_validators import CREAtlasValidator

        v = CREAtlasValidator()
        result = await v.validate_attempt(
            task_payload={},
            attempt_output={
                "property_type": "industrial",
                "location": "Dallas, TX",
                "valuation": -500_000,
                "zoning": "M-1",
            },
            objective_score=0.5,
        )
        assert "invalid_valuation:non_positive" in result.flags
        assert result.confidence < 0.5

    @pytest.mark.asyncio
    async def test_no_risk_factors_flagged(self):
        from swarmchain.services.domain_validators import CREAtlasValidator

        v = CREAtlasValidator()
        result = await v.validate_attempt(
            task_payload={},
            attempt_output={
                "property_type": "multifamily",
                "location": "Austin, TX",
                "valuation": 8_000_000,
                "zoning": "R-3",
                "risk_factors": [],
            },
            objective_score=0.7,
        )
        assert "no_risk_factors_identified" in result.flags
        assert "every cre asset has risks" in result.critique.lower()

    @pytest.mark.asyncio
    async def test_repair_suggestion_for_missing_sections(self):
        from swarmchain.services.domain_validators import CREAtlasValidator

        v = CREAtlasValidator()
        result = await v.validate_attempt(
            task_payload={},
            attempt_output={"property_type": "hotel"},
            objective_score=0.1,
        )
        assert result.repair_suggestion is not None
        assert "location" in result.repair_suggestion.lower()


# ─── Unit: Scaffold Validators ─────────────────────────────────


class TestCapitalValidator:
    @pytest.mark.asyncio
    async def test_all_fields_present_approved(self):
        from swarmchain.services.domain_validators import CapitalValidator

        v = CapitalValidator()
        result = await v.validate_attempt(
            task_payload={"required_fields": ["amount", "type", "eligibility"]},
            attempt_output={"amount": 50000, "type": "SBA", "eligibility": True},
            objective_score=0.9,
        )
        assert result.verdict == "approved"
        assert len(result.flags) == 0

    @pytest.mark.asyncio
    async def test_missing_fields_flagged(self):
        from swarmchain.services.domain_validators import CapitalValidator

        v = CapitalValidator()
        result = await v.validate_attempt(
            task_payload={"required_fields": ["amount", "type", "eligibility"]},
            attempt_output={"amount": 50000},
            objective_score=0.5,
        )
        assert result.verdict == "flagged"
        assert len(result.flags) == 2


class TestLegalResolveValidator:
    @pytest.mark.asyncio
    async def test_full_irac_approved(self):
        from swarmchain.services.domain_validators import LegalResolveValidator

        v = LegalResolveValidator()
        result = await v.validate_attempt(
            task_payload={},
            attempt_output={
                "issue": "Contract breach",
                "rule": "UCC 2-301",
                "analysis": "Seller failed to deliver...",
                "conclusion": "Buyer entitled to damages",
            },
            objective_score=0.95,
        )
        assert result.verdict == "approved"
        assert result.confidence == 1.0


# ─── Unit: Registry ────────────────────────────────────────────


class TestValidatorRegistry:
    def test_cre_registered(self):
        from swarmchain.services.domain_validators import get_validator
        v = get_validator("cre")
        assert v is not None
        assert v.name == "atlas-cre"

    def test_capital_registered(self):
        from swarmchain.services.domain_validators import get_validator
        v = get_validator("capital")
        assert v is not None
        assert v.name == "swarm-capital-27b"

    def test_legal_registered(self):
        from swarmchain.services.domain_validators import get_validator
        v = get_validator("legal")
        assert v is not None
        assert v.name == "resolve-legal"

    def test_arc_has_no_validator(self):
        from swarmchain.services.domain_validators import get_validator
        assert get_validator("arc") is None

    def test_unknown_domain_returns_none(self):
        from swarmchain.services.domain_validators import get_validator
        assert get_validator("crypto") is None


# ─── Iron Rule: Validators Cannot Override Objective ───────────


class TestIronRule:
    """The most important tests: validators may NEVER override objective verification."""

    @pytest.mark.asyncio
    async def test_validator_cannot_reject_objectively_solved(self, test_client: AsyncClient):
        """If objective score is 1.0, validator verdict is forced to approved."""
        from swarmchain.services.domain_validators import ValidatorRunner, CREAtlasValidator
        from swarmchain.db.models import Block, Attempt, ValidatorDecision
        from swarmchain.db.engine import async_session_factory

        async with async_session_factory() as db:
            # Create a CRE block that is objectively solved
            from swarmchain.db.models import Node
            node = Node(node_id="iron-rule-node", node_type="test", hardware_class="cpu")
            db.add(node)
            await db.flush()

            block = Block(
                block_id="iron-rule-block",
                task_id="cre-test",
                domain="cre",
                status="solved",
                task_payload={},
                final_score=1.0,
            )
            db.add(block)
            await db.flush()

            # Attempt with empty CRE data — validator would normally reject
            attempt = Attempt(
                attempt_id="iron-rule-attempt",
                block_id="iron-rule-block",
                node_id="iron-rule-node",
                output_json={},  # empty — validator would flag everything
                score=1.0,
                valid=True,
            )
            db.add(attempt)
            await db.flush()

            # Run validator
            decision = await ValidatorRunner.run_validator(
                db, block, attempt, objective_score=1.0
            )
            await db.commit()

        # The iron rule: validator CANNOT reject when objective says solved
        assert decision is not None
        assert decision.verdict == "approved"  # forced to approved
        assert decision.objective_overridden is False or "validator_overridden_by_objective" in (decision.flags or [])

    @pytest.mark.asyncio
    async def test_validator_stores_decision_in_db(self, test_client: AsyncClient):
        """Validator decisions are persisted."""
        from swarmchain.db.engine import async_session_factory
        from swarmchain.db.models import ValidatorDecision, BlockArtifact, Block, Attempt, Node
        from swarmchain.services.domain_validators import ValidatorRunner
        from sqlalchemy import select

        async with async_session_factory() as db:
            node = Node(node_id="store-test-node", node_type="test", hardware_class="cpu")
            db.add(node)
            await db.flush()

            block = Block(
                block_id="store-test-block",
                task_id="cre-store",
                domain="cre",
                status="solved",
                task_payload={},
                final_score=0.8,
            )
            db.add(block)
            await db.flush()

            attempt = Attempt(
                attempt_id="store-test-attempt",
                block_id="store-test-block",
                node_id="store-test-node",
                output_json={"property_type": "office", "location": "NYC", "valuation": 1e7, "zoning": "C5"},
                score=0.8,
                valid=True,
            )
            db.add(attempt)
            await db.flush()

            await ValidatorRunner.run_validator(db, block, attempt, 0.8)
            await db.commit()

            # Check decision was stored
            result = await db.execute(
                select(ValidatorDecision).where(ValidatorDecision.block_id == "store-test-block")
            )
            decisions = result.scalars().all()
            assert len(decisions) == 1
            assert decisions[0].validator_name == "atlas-cre"

            # Check artifact was stored
            result = await db.execute(
                select(BlockArtifact)
                .where(BlockArtifact.block_id == "store-test-block")
                .where(BlockArtifact.artifact_type == "validator_decision")
            )
            artifacts = result.scalars().all()
            assert len(artifacts) == 1
            assert artifacts[0].artifact_json["validator_name"] == "atlas-cre"


# ─── API: Validator Endpoints ──────────────────────────────────


class TestValidatorAPI:
    @pytest.mark.asyncio
    async def test_list_validators(self, test_client: AsyncClient):
        resp = await test_client.get("/validators")
        assert resp.status_code == 200
        data = resp.json()
        assert "validators" in data
        names = [v["name"] for v in data["validators"]]
        assert "atlas-cre" in names
        assert "swarm-capital-27b" in names
        assert "resolve-legal" in names

    @pytest.mark.asyncio
    async def test_get_validations_empty(self, test_client: AsyncClient):
        """Block with no validator decisions returns empty list."""
        # Create a block first
        resp = await test_client.post("/blocks/open", json={
            "task_id": "arc-001-fill-blue",
            "domain": "arc",
            "task_payload": {"input_grid": [[0]], "expected_output": [[1]]},
        })
        block_id = resp.json()["block_id"]

        resp = await test_client.get(f"/blocks/{block_id}/validations")
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_validator"] is False
        assert data["decisions"] == []
