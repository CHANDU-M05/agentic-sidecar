"""Full-plan boundary and evaluator context contracts."""

from agentic_sidecar import (
    CriticEvaluator,
    DecisionContext,
    JudgeEvaluator,
    MockJudge,
    PlanEvaluator,
    Sidecar,
)
from agentic_sidecar.gate import PolicyAdvisor, PolicyRule
from agentic_sidecar.intent import ConstraintBinding, IntentEnvelope, IntentGuardian


def test_full_plan_checks_constraints_on_every_step():
    guardian = IntentGuardian(
        IntentEnvelope(
            goal="Refund customer", requested_by={"id": "u"}, constraints={"maximum_refund": 500}
        ),
        [ConstraintBinding(constraint="maximum_refund", tool="issue_refund", arg_name="amount")],
    )
    sidecar = Sidecar(
        on_sidecar_failure="fail_closed",
        roles=["intent_guardian", "planner"],
        intent=guardian,
        planner=PlanEvaluator(),
    )
    assert (
        sidecar.evaluate_plan(
            [{"tool_name": "read"}, {"tool_name": "issue_refund", "arguments": {"amount": 850}}]
        ).status
        == "BLOCK"
    )
    decision = sidecar.evaluate_plan([{"tool_name": "issue_refund", "arguments": {"amount": 120}}])
    assert decision.status == "ALLOW"
    assert decision.decision_point == "plan"


def test_plan_boundary_does_not_recheck_synthetic_marker_against_policy_or_risk():
    # A default-deny policy allowlisting only the real steps must not BLOCK the
    # plan via the synthetic "__plan__" marker, which matches no allow rule.
    sidecar = Sidecar(
        on_sidecar_failure="fail_closed",
        roles=["policy", "risk"],
        policy=PolicyAdvisor([PolicyRule(tool="read", effect="allow")], default_effect="deny"),
    )
    decision = sidecar.evaluate_plan([{"tool_name": "read"}])
    assert decision.status == "ALLOW"
    assert decision.decision_point == "plan"


def test_plan_boundary_preserves_warn_from_a_step_constraint():
    guardian = IntentGuardian(
        IntentEnvelope(
            goal="Refund customer", requested_by={"id": "u"}, constraints={"maximum_refund": 500}
        ),
        [
            ConstraintBinding(
                constraint="maximum_refund",
                tool="issue_refund",
                arg_name="amount",
                severity="WARN",
            )
        ],
    )
    sidecar = Sidecar(on_sidecar_failure="fail_closed", roles=["intent_guardian"], intent=guardian)
    decision = sidecar.evaluate_plan([{"tool_name": "issue_refund", "arguments": {"amount": 850}}])
    assert decision.status == "WARN"
    assert "maximum_refund" in decision.reason


def test_plan_goal_language_and_contradictions():
    sidecar = Sidecar(on_sidecar_failure="fail_closed", roles=["planner"], planner=PlanEvaluator())
    assert (
        sidecar.evaluate_plan(
            [{"tool_name": "cancel_subscription"}], goal="Cancel my subscription"
        ).status
        == "ALLOW"
    )
    assert (
        sidecar.evaluate_plan([{"tool_name": "issue_refund"}], goal="Explain the charge").status
        == "REPLAN"
    )
    assert (
        sidecar.evaluate_plan(
            [{"tool_name": "approve"}, {"tool_name": "reject"}], goal="Review"
        ).status
        == "REPLAN"
    )


def test_evaluators_receive_goal_constraints_history_metadata_and_plan():
    observed = []

    class Capture(MockJudge):
        def evaluate(self, question, context):
            observed.append(context)
            return super().evaluate(question, context)

    guardian = IntentGuardian(
        IntentEnvelope(goal="Review account", requested_by={"id": "u"}, constraints={"limit": 10})
    )
    sidecar = Sidecar(
        on_sidecar_failure="fail_closed",
        roles=["intent_guardian", "judge"],
        intent=guardian,
        judge=JudgeEvaluator(Capture()),
    )
    sidecar.evaluate(DecisionContext(tool_name="read"))
    plan = [{"tool_name": "read", "arguments": {"id": 1}}]
    sidecar.evaluate_plan(plan, metadata={"trace_id": "t"})
    context = observed[-1]
    assert context["goal"] == "Review account"
    assert context["constraints"] == {"limit": 10}
    assert context["history"][0]["tool_name"] == "read"
    assert context["plan"] == plan
    assert context["metadata"] == {"trace_id": "t"}
    assert context["boundary"] == "plan"


def test_invalid_plan_uses_failure_policy():
    for failure, status in [("fail_closed", "BLOCK"), ("fail_open", "ALLOW")]:
        sidecar = Sidecar(on_sidecar_failure=failure, roles=["planner"], planner=PlanEvaluator())
        assert sidecar.evaluate_plan([]).status == status
        assert sidecar.evaluate_plan([{}]).status == status


def test_critic_evidence_and_history_challenges():
    critic = CriticEvaluator()
    assert critic.evaluate({"tool_name": "issue_refund"}).status == "CHALLENGE"
    assert (
        critic.evaluate(
            {
                "tool_name": "issue_refund",
                "metadata": {"authorized": True, "eligibility_verified": True},
            }
        ).status
        == "ALLOW"
    )
    assert (
        critic.evaluate(
            {
                "tool_name": "delete_account",
                "metadata": {"authorized": True, "backup_verified": True},
            }
        ).status
        == "ALLOW"
    )
    assert (
        critic.evaluate(
            {"tool_name": "reject", "history": [{"tool_name": "approve", "status": "ALLOW"}]}
        ).status
        == "CHALLENGE"
    )
