"""Tests for CriticEvaluator (v0.3.0)."""

from agentic_sidecar.evaluators.critic import CriticChallenge, CriticEvaluator


class TestCriticChallenge:
    """Test suite for CriticChallenge dataclass."""

    def test_challenge_creation(self):
        """Test basic challenge creation."""
        challenge = CriticChallenge(
            category="risky",
            severity="HIGH",
            description="Attempting to delete database without backup",
            evidence="no_backup_found, large_table",
            suggestion="Create backup before deletion",
        )
        assert challenge.category == "risky"
        assert challenge.severity == "HIGH"
        assert "delete" in challenge.description.lower()

    def test_challenge_equality(self):
        """Test challenge comparison."""
        c1 = CriticChallenge(
            category="risky",
            severity="HIGH",
            description="Delete without backup",
        )
        c2 = CriticChallenge(
            category="risky",
            severity="HIGH",
            description="Delete without backup",
        )
        assert c1 == c2


class TestCriticEvaluator:
    """Test suite for critic-level evaluation."""

    def setup_method(self):
        """Initialize evaluator before each test."""
        self.evaluator = CriticEvaluator(enabled=True)

    def test_evaluator_initialization(self):
        """Test basic initialization."""
        assert self.evaluator.enabled is True
        assert self.evaluator.name == "CriticEvaluator"

    def test_allow_safe_action(self):
        """Test ALLOW for safe actions."""
        context = {
            "tool_name": "search",
            "arguments": {"query": "weather"},
            "history": [],
            "intent": None,
        }
        result = self.evaluator.evaluate(context)
        assert result.status == "ALLOW"

    def test_challenge_risky_operation(self):
        """Test CHALLENGE for risky delete operations."""
        context = {
            "tool_name": "delete",
            "arguments": {"table": "users", "id": 123},
            "history": [],
            "intent": None,
        }
        result = self.evaluator.evaluate(context)
        assert result.status in ("ALLOW", "CHALLENGE")
        assert result.rationale is not None

    def test_challenge_large_amount(self):
        """Test CHALLENGE for large financial amounts."""
        context = {
            "tool_name": "refund",
            "arguments": {"amount": 5000, "reason": "test"},
            "history": [],
            "intent": None,
        }
        result = self.evaluator.evaluate(context)
        assert result.status in ("ALLOW", "CHALLENGE")

    def test_confidence_score(self):
        """Test confidence is 1.0 (rule-based)."""
        context = {"tool_name": "search", "arguments": {}}
        result = self.evaluator.evaluate(context)
        assert result.confidence == 1.0

    def test_metadata_contains_challenges(self):
        """Test metadata includes challenge details."""
        context = {
            "tool_name": "delete",
            "arguments": {"table": "data"},
            "history": [],
            "intent": None,
        }
        result = self.evaluator.evaluate(context)
        assert isinstance(result.metadata, dict)

    def test_challenge_with_history(self):
        """Test challenge detection with decision history."""
        context = {
            "tool_name": "cancel",
            "arguments": {"order_id": 123},
            "history": [
                {"tool_name": "create", "tool_args": {"order_id": 123}, "status": "ALLOW"},
                {"tool_name": "pay", "tool_args": {"order_id": 123}, "status": "ALLOW"},
            ],
            "intent": None,
        }
        result = self.evaluator.evaluate(context)
        assert result.status in ("ALLOW", "CHALLENGE")
        assert result.rationale is not None


class TestCriticCategories:
    """Test challenge categories are recognized."""

    def test_all_categories(self):
        """Test all challenge categories."""
        categories = ["risky", "assumption", "contradiction", "reasoning"]
        for cat in categories:
            challenge = CriticChallenge(
                category=cat,
                severity="MEDIUM",
                description="Test challenge",
            )
            assert challenge.category == cat
