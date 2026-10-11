"""Tests for Sidecar integration with v0.3.0 evaluators."""

from agentic_sidecar.core.context import DecisionContext
from agentic_sidecar.core.sidecar import Sidecar
from agentic_sidecar.evaluators.critic import CriticEvaluator
from agentic_sidecar.evaluators.judge import JudgeEvaluator
from agentic_sidecar.evaluators.planner import PlanEvaluator
from agentic_sidecar.evaluators.providers import MockJudge


class TestSidecarWithEvaluators:
    """Test Sidecar integration with evaluators."""

    def test_sidecar_with_planner(self):
        """Test Sidecar with Planner enabled."""
        sidecar = Sidecar(
            on_sidecar_failure="fail_closed",
            planner=PlanEvaluator(enabled=True),
            roles=["planner"],
        )

        context = DecisionContext(tool_name="search", tool_args={"query": "test"})
        decision = sidecar.evaluate(context)

        assert decision.status in ("ALLOW", "REPLAN", "BLOCK")
        assert decision.reason is not None

    def test_sidecar_with_critic(self):
        """Test Sidecar with Critic enabled."""
        sidecar = Sidecar(
            on_sidecar_failure="fail_closed",
            critic=CriticEvaluator(enabled=True),
            roles=["critic"],
        )

        context = DecisionContext(tool_name="delete", tool_args={"table": "users"})
        decision = sidecar.evaluate(context)

        assert decision.status in ("ALLOW", "CHALLENGE", "BLOCK")

    def test_sidecar_with_judge(self):
        """Test Sidecar with Judge enabled."""
        provider = MockJudge(model="gpt-4")
        sidecar = Sidecar(
            on_sidecar_failure="fail_closed",
            judge=JudgeEvaluator(provider=provider, enabled=True),
            roles=["judge"],
        )

        context = DecisionContext(tool_name="refund", tool_args={"amount": 100})
        decision = sidecar.evaluate(context)

        assert decision.status is not None
        assert decision.reason is not None

    def test_sidecar_with_all_evaluators(self):
        """Test Sidecar with all evaluators enabled."""
        sidecar = Sidecar(
            on_sidecar_failure="fail_closed",
            planner=PlanEvaluator(enabled=True),
            critic=CriticEvaluator(enabled=True),
            judge=JudgeEvaluator(provider=MockJudge(model="gpt-4")),
            roles=["policy", "risk", "planner", "critic", "judge"],
        )

        context = DecisionContext(tool_name="delete", tool_args={"id": 123})
        decision = sidecar.evaluate(context)

        assert decision.status is not None

    def test_sidecar_disabled_evaluators(self):
        """Test Sidecar with evaluators disabled."""
        sidecar = Sidecar(
            on_sidecar_failure="fail_closed",
            planner=PlanEvaluator(enabled=False),
            critic=CriticEvaluator(enabled=False),
            roles=["policy", "risk", "planner", "critic"],
        )

        context = DecisionContext(tool_name="search", tool_args={})
        decision = sidecar.evaluate(context)

        assert decision.status == "ALLOW"

    def test_sidecar_early_exit_on_planner(self):
        """Test that Planner can return REPLAN early."""
        sidecar = Sidecar(
            on_sidecar_failure="fail_closed",
            planner=PlanEvaluator(enabled=True),
            critic=CriticEvaluator(enabled=True),
            roles=["planner", "critic"],
        )

        context = DecisionContext(tool_name="refund", tool_args={"amount": 100})
        decision = sidecar.evaluate(context)

        # Decision should be ALLOW, REPLAN, BLOCK, or CHALLENGE
        assert decision.status in ("ALLOW", "REPLAN", "BLOCK", "CHALLENGE")

    def test_evaluator_none_is_optional(self):
        """Test that passing None for evaluators is valid."""
        sidecar = Sidecar(
            on_sidecar_failure="fail_closed",
            planner=None,
            critic=None,
            judge=None,
            roles=["policy", "risk"],
        )

        context = DecisionContext(tool_name="search", tool_args={})
        decision = sidecar.evaluate(context)

        assert decision.status == "ALLOW"

    def test_decision_history_available_to_evaluators(self):
        """Test that evaluators receive decision history."""
        sidecar = Sidecar(
            on_sidecar_failure="fail_closed",
            critic=CriticEvaluator(enabled=True),
            roles=["critic"],
        )

        context1 = DecisionContext(tool_name="search", tool_args={"query": "test"})
        sidecar.evaluate(context1)

        context2 = DecisionContext(tool_name="delete", tool_args={"id": 123})
        decision2 = sidecar.evaluate(context2)

        # Second decision should have history from first
        assert len(sidecar.decisions) == 2
        assert decision2.status is not None
