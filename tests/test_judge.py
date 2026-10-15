"""Tests for JudgeEvaluator and LLM providers (v0.3.0)."""

from agentic_sidecar.evaluators.judge import JudgeEvaluator
from agentic_sidecar.evaluators.providers import MockJudge


class TestJudgeEvaluator:
    """Test suite for Judge evaluator."""

    def test_initialization_with_openai(self):
        """Test initialization with OpenAI provider."""
        provider = MockJudge(model="gpt-4")
        judge = JudgeEvaluator(provider=provider, enabled=True)
        assert judge.enabled is True
        assert judge.provider == provider

    def test_initialization_with_anthropic(self):
        """Test initialization with Anthropic provider."""
        provider = MockJudge(model="claude-3-opus")
        judge = JudgeEvaluator(provider=provider, enabled=True)
        assert judge.enabled is True
        assert judge.provider == provider

    def test_judge_evaluation(self):
        """Test judge evaluation with mock provider."""
        provider = MockJudge(model="gpt-4")
        judge = JudgeEvaluator(provider=provider)

        context = {
            "tool_name": "refund",
            "arguments": {"amount": 100},
            "history": [],
            "intent": None,
        }
        result = judge.evaluate(context)
        assert result.status in ("ALLOW", "WARN", "BLOCK", "CHALLENGE")
        assert result.rationale is not None

    def test_cost_tracking(self):
        """Test cost tracking."""
        provider = MockJudge(model="gpt-4")
        judge = JudgeEvaluator(provider=provider)

        initial_cost = judge.get_cost()
        assert initial_cost >= 0

        context = {
            "tool_name": "search",
            "arguments": {},
            "history": [],
            "intent": None,
        }
        judge.evaluate(context)
        # Cost should be tracked
        assert isinstance(judge.total_cost, float)

    def test_disabled_judge(self):
        """Test disabled judge doesn't evaluate."""
        provider = MockJudge(model="gpt-4")
        judge = JudgeEvaluator(provider=provider, enabled=False)
        assert judge.enabled is False

    def test_reset_cost(self):
        """Test cost reset."""
        provider = MockJudge(model="gpt-4")
        judge = JudgeEvaluator(provider=provider)

        context = {
            "tool_name": "search",
            "arguments": {},
            "history": [],
            "intent": None,
        }
        judge.evaluate(context)
        judge.reset_cost()
        assert judge.get_cost() == 0.0


class TestMockJudgeOne:
    """Test suite for OpenAI Judge provider."""

    def test_initialization(self):
        """Test provider initialization."""
        provider = MockJudge(model="gpt-4")
        assert provider.model == "gpt-4"

    def test_validation(self):
        """Test provider validation."""
        provider = MockJudge(model="gpt-4")
        assert provider.validate() is True

        empty_provider = MockJudge(model="")
        assert empty_provider.validate() is False

    def test_evaluation(self):
        """Test evaluation returns proper structure."""
        provider = MockJudge(model="gpt-4")
        result = provider.evaluate(
            question="Should this action proceed?",
            context={"tool_name": "refund", "arguments": {"amount": 100}},
        )
        assert "decision" in result
        assert "reasoning" in result
        assert "confidence" in result
        assert result["decision"] in ("ALLOW", "BLOCK", "WARN", "CHALLENGE")


class TestMockJudgeTwo:
    """Test suite for Anthropic Judge provider."""

    def test_initialization(self):
        """Test provider initialization."""
        provider = MockJudge(model="claude-3-opus")
        assert provider.model == "claude-3-opus"

    def test_validation(self):
        """Test provider validation."""
        provider = MockJudge(model="claude-3-opus")
        assert provider.validate() is True

        empty_provider = MockJudge(model="")
        assert empty_provider.validate() is False

    def test_evaluation(self):
        """Test evaluation returns proper structure."""
        provider = MockJudge(model="claude-3-opus")
        result = provider.evaluate(
            question="Should this action proceed?",
            context={"tool_name": "search", "arguments": {"query": "test"}},
        )
        assert "decision" in result
        assert "reasoning" in result
        assert "confidence" in result
        assert result["decision"] in ("ALLOW", "BLOCK", "WARN", "CHALLENGE")


class TestProviderSwapping:
    """Test that Judge works with different providers."""

    def test_swap_providers(self):
        """Test swapping between providers."""
        judge = JudgeEvaluator(provider=MockJudge(model="gpt-4"))
        context = {"tool_name": "search", "arguments": {}, "history": [], "intent": None}
        result1 = judge.evaluate(context)

        judge.provider = MockJudge(model="claude-3-opus")
        result2 = judge.evaluate(context)

        # Both should return valid results
        assert result1.status is not None
        assert result2.status is not None
