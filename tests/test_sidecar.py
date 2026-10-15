"""Tests for `agentic_sidecar.core.sidecar.Sidecar`, including the
`on_sidecar_failure` fail_open/fail_closed paths (ROADMAP.md's Design
Constraint 3 -- these must always be exercised).
"""

from datetime import datetime, timedelta, timezone

import pytest

from agentic_sidecar.core.context import DecisionContext
from agentic_sidecar.core.decision import Decision
from agentic_sidecar.core.sidecar import Sidecar
from agentic_sidecar.gate.policy import PolicyAdvisor, PolicyRule
from agentic_sidecar.gate.risk import RiskEvaluator, RiskResult, RiskRule
from agentic_sidecar.intent.alignment import AlignmentResult, ConstraintBinding, IntentGuardian
from agentic_sidecar.intent.envelope import IntentEnvelope, Requester

REFUND_BINDING = ConstraintBinding(
    constraint="maximum_refund", tool="issue_refund", arg_name="amount", op="lte"
)


def _refund_guardian(**envelope_overrides: object) -> IntentGuardian:
    defaults: dict[str, object] = {
        "goal": "refund_customer",
        "requested_by": Requester(type="human", id="user123"),
        "constraints": {"maximum_refund": 500},
    }
    defaults.update(envelope_overrides)
    envelope = IntentEnvelope.model_validate(defaults)
    return IntentGuardian(envelope, [REFUND_BINDING])


def test_on_sidecar_failure_is_required() -> None:
    with pytest.raises(TypeError):
        Sidecar()  # type: ignore[call-arg]


def test_on_sidecar_failure_rejects_invalid_value() -> None:
    with pytest.raises(ValueError, match="on_sidecar_failure"):
        Sidecar(on_sidecar_failure="maybe")  # type: ignore[arg-type]


def test_invalid_risk_block_threshold_rejected_at_construction() -> None:
    with pytest.raises(ValueError, match="risk_block_threshold"):
        Sidecar(on_sidecar_failure="fail_open", risk_block_threshold="SEVERE")  # type: ignore[arg-type]


def test_invalid_mode_rejected() -> None:
    with pytest.raises(ValueError, match="mode"):
        Sidecar(on_sidecar_failure="fail_closed", mode="advise")  # type: ignore[arg-type]


def test_govern_mode_is_accepted() -> None:
    sidecar = Sidecar(on_sidecar_failure="fail_closed", mode="govern")
    assert sidecar.mode == "govern"


def test_evaluate_never_raises_for_block_regardless_of_mode() -> None:
    """`evaluate()` only computes a Decision -- enforcing a BLOCK (actually
    stopping the call) is the attached adapter's job, not core's. See
    `agentic_sidecar.core.exceptions.SidecarBlockedError`."""
    for mode in ("observe", "govern"):
        sidecar = Sidecar(
            on_sidecar_failure="fail_closed",
            policy=PolicyAdvisor(default_effect="deny"),
            mode=mode,  # type: ignore[arg-type]
        )
        decision = sidecar.evaluate(DecisionContext(tool_name="anything"))
        assert decision.status == "BLOCK"


def test_default_deny_all_policy_blocks() -> None:
    sidecar = Sidecar(
        on_sidecar_failure="fail_closed",
        policy=PolicyAdvisor(default_effect="deny"),
    )
    decision = sidecar.evaluate(DecisionContext(tool_name="anything"))
    assert decision.status == "BLOCK"
    assert "Policy Advisor" in decision.reason


def test_allowed_low_risk_action_allows() -> None:
    sidecar = Sidecar(on_sidecar_failure="fail_closed")
    decision = sidecar.evaluate(DecisionContext(tool_name="read_order"))
    assert decision.status == "ALLOW"
    assert decision.risk == "LOW"


def test_high_risk_action_blocks_at_default_threshold() -> None:
    sidecar = Sidecar(
        on_sidecar_failure="fail_closed",
        risk=RiskEvaluator([RiskRule(tool="delete_*", risk="HIGH")]),
    )
    decision = sidecar.evaluate(DecisionContext(tool_name="delete_database"))
    assert decision.status == "BLOCK"
    assert decision.risk == "HIGH"


def test_medium_risk_allows_when_threshold_is_high() -> None:
    sidecar = Sidecar(
        on_sidecar_failure="fail_closed",
        risk=RiskEvaluator([RiskRule(tool="archive_*", risk="MEDIUM")]),
        risk_block_threshold="HIGH",
    )
    decision = sidecar.evaluate(DecisionContext(tool_name="archive_order"))
    assert decision.status == "ALLOW"
    assert decision.risk == "MEDIUM"


def test_custom_risk_block_threshold_blocks_medium() -> None:
    sidecar = Sidecar(
        on_sidecar_failure="fail_closed",
        risk=RiskEvaluator([RiskRule(tool="archive_*", risk="MEDIUM")]),
        risk_block_threshold="MEDIUM",
    )
    decision = sidecar.evaluate(DecisionContext(tool_name="archive_order"))
    assert decision.status == "BLOCK"


def test_policy_deny_short_circuits_before_risk_runs() -> None:
    calls: list[str] = []

    class _TrackingRiskEvaluator(RiskEvaluator):
        def evaluate(self, context: DecisionContext) -> RiskResult:
            calls.append(context.tool_name)
            return super().evaluate(context)

    sidecar = Sidecar(
        on_sidecar_failure="fail_closed",
        policy=PolicyAdvisor([PolicyRule(tool="delete_*", effect="deny")]),
        risk=_TrackingRiskEvaluator(),
    )
    decision = sidecar.evaluate(DecisionContext(tool_name="delete_database"))
    assert decision.status == "BLOCK"
    assert calls == []


def test_fail_open_allows_when_hook_raises() -> None:
    sidecar = Sidecar(on_sidecar_failure="fail_open")

    @sidecar.before_tool_call
    def broken_hook(context: DecisionContext) -> Decision:
        raise RuntimeError("evaluator exploded")

    decision = sidecar.evaluate(DecisionContext(tool_name="anything"))
    assert decision.status == "ALLOW"
    assert decision.risk is None
    assert "RuntimeError" in decision.reason


def test_fail_closed_blocks_when_hook_raises() -> None:
    sidecar = Sidecar(on_sidecar_failure="fail_closed")

    @sidecar.before_tool_call
    def broken_hook(context: DecisionContext) -> Decision:
        raise RuntimeError("evaluator exploded")

    decision = sidecar.evaluate(DecisionContext(tool_name="anything"))
    assert decision.status == "BLOCK"
    assert decision.risk is None


def test_custom_hook_overrides_default_evaluation() -> None:
    sidecar = Sidecar(
        on_sidecar_failure="fail_closed",
        policy=PolicyAdvisor(default_effect="deny"),  # would otherwise block everything
    )

    @sidecar.before_tool_call
    def always_allow(context: DecisionContext) -> Decision:
        return Decision(status="ALLOW", risk="LOW", reason="custom hook allows everything")

    decision = sidecar.evaluate(DecisionContext(tool_name="anything"))
    assert decision.status == "ALLOW"
    assert decision.reason == "custom hook allows everything"


def test_every_evaluation_is_recorded() -> None:
    sidecar = Sidecar(on_sidecar_failure="fail_closed")
    context = DecisionContext(tool_name="read_order")
    decision = sidecar.evaluate(context)
    assert sidecar.decisions == [(context, decision)]


def test_unknown_role_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown role"):
        Sidecar(on_sidecar_failure="fail_closed", roles=["not_a_role"])


def test_disabling_policy_role_skips_it() -> None:
    sidecar = Sidecar(
        on_sidecar_failure="fail_closed",
        policy=PolicyAdvisor(default_effect="deny"),
        roles=["risk"],
    )
    decision = sidecar.evaluate(DecisionContext(tool_name="anything"))
    assert decision.status == "ALLOW"


def test_disabling_risk_role_skips_it() -> None:
    sidecar = Sidecar(
        on_sidecar_failure="fail_closed",
        risk=RiskEvaluator(default_risk="HIGH"),
        roles=["policy"],
    )
    decision = sidecar.evaluate(DecisionContext(tool_name="anything"))
    assert decision.status == "ALLOW"
    assert decision.risk is None


# --- Intent Guardian (v0.2) --------------------------------------------------


def test_intent_without_role_enabled_raises() -> None:
    with pytest.raises(ValueError, match="intent_guardian"):
        Sidecar(
            on_sidecar_failure="fail_closed",
            intent=_refund_guardian(),
            roles=["policy", "risk"],
        )


def test_set_intent_without_role_enabled_raises() -> None:
    sidecar = Sidecar(on_sidecar_failure="fail_closed", roles=["policy", "risk"])
    with pytest.raises(ValueError, match="intent_guardian"):
        sidecar.set_intent(_refund_guardian())


def test_intent_guardian_role_enabled_but_no_envelope_yet_is_a_noop() -> None:
    sidecar = Sidecar(on_sidecar_failure="fail_closed", roles=["policy", "risk", "intent_guardian"])
    decision = sidecar.evaluate(
        DecisionContext(tool_name="issue_refund", tool_args={"amount": 999})
    )
    assert decision.status == "ALLOW"


def test_intent_guardian_blocks_refund_over_limit() -> None:
    """The refund-limit scenario from concept.md §9, end to end through
    `Sidecar.evaluate()`."""
    sidecar = Sidecar(
        on_sidecar_failure="fail_closed",
        roles=["policy", "risk", "intent_guardian"],
        intent=_refund_guardian(),
    )
    decision = sidecar.evaluate(
        DecisionContext(tool_name="issue_refund", tool_args={"amount": 850})
    )
    assert decision.status == "BLOCK"
    assert "Intent Guardian" in decision.reason
    assert "maximum_refund" in decision.reason


def test_intent_guardian_allows_refund_within_limit() -> None:
    sidecar = Sidecar(
        on_sidecar_failure="fail_closed",
        roles=["policy", "risk", "intent_guardian"],
        intent=_refund_guardian(),
    )
    decision = sidecar.evaluate(
        DecisionContext(tool_name="issue_refund", tool_args={"amount": 120})
    )
    assert decision.status == "ALLOW"


def test_intent_guardian_warns_on_expired_envelope() -> None:
    past = datetime.now(timezone.utc) - timedelta(days=1)
    sidecar = Sidecar(
        on_sidecar_failure="fail_closed",
        roles=["policy", "risk", "intent_guardian"],
        intent=_refund_guardian(expires=past),
    )
    decision = sidecar.evaluate(DecisionContext(tool_name="issue_refund", tool_args={"amount": 10}))
    assert decision.status == "WARN"
    assert "expired" in decision.reason


def test_set_intent_updates_the_active_envelope() -> None:
    sidecar = Sidecar(on_sidecar_failure="fail_closed", roles=["policy", "risk", "intent_guardian"])
    over_limit = DecisionContext(tool_name="issue_refund", tool_args={"amount": 850})
    assert sidecar.evaluate(over_limit).status == "ALLOW"  # no envelope set yet

    sidecar.set_intent(_refund_guardian())
    assert sidecar.evaluate(over_limit).status == "BLOCK"

    sidecar.set_intent(None)
    assert sidecar.evaluate(over_limit).status == "ALLOW"


def test_policy_and_risk_still_short_circuit_before_intent_guardian_runs() -> None:
    calls: list[str] = []

    class _TrackingGuardian(IntentGuardian):
        def evaluate(self, context: DecisionContext) -> AlignmentResult:
            calls.append(context.tool_name)
            return super().evaluate(context)

    envelope = _refund_guardian().envelope
    sidecar = Sidecar(
        on_sidecar_failure="fail_closed",
        policy=PolicyAdvisor([PolicyRule(tool="issue_refund", effect="deny")]),
        roles=["policy", "risk", "intent_guardian"],
        intent=_TrackingGuardian(envelope, [REFUND_BINDING]),
    )
    decision = sidecar.evaluate(
        DecisionContext(tool_name="issue_refund", tool_args={"amount": 850})
    )
    assert decision.status == "BLOCK"
    assert calls == []


def test_evaluate_injects_intent_snapshot_into_recorded_context() -> None:
    sidecar = Sidecar(
        on_sidecar_failure="fail_closed",
        roles=["policy", "risk", "intent_guardian"],
        intent=_refund_guardian(),
    )
    sidecar.evaluate(DecisionContext(tool_name="issue_refund", tool_args={"amount": 100}))
    recorded_context, _ = sidecar.decisions[0]
    assert recorded_context.intent is not None
    assert recorded_context.intent.goal == "refund_customer"
    assert recorded_context.intent.constraints == {"maximum_refund": 500}


def test_evaluate_mutates_the_callers_context_in_place() -> None:
    """`evaluate()` must inject intent/history onto the exact object the
    caller passed in (not a copy) -- an adapter building
    `SidecarBlockedError` after the call relies on this to report the
    context Intent Guardian actually saw."""
    sidecar = Sidecar(
        on_sidecar_failure="fail_closed",
        roles=["policy", "risk", "intent_guardian"],
        intent=_refund_guardian(),
    )
    context = DecisionContext(tool_name="issue_refund", tool_args={"amount": 100})
    assert context.intent is None

    sidecar.evaluate(context)

    assert context.intent is not None
    assert context.intent.goal == "refund_customer"
    assert context == sidecar.decisions[0][0]
    assert context is not sidecar.decisions[0][0]


def test_evaluate_injects_growing_history_into_recorded_context() -> None:
    sidecar = Sidecar(on_sidecar_failure="fail_closed")
    sidecar.evaluate(DecisionContext(tool_name="look_up_order"))
    sidecar.evaluate(DecisionContext(tool_name="issue_refund", tool_args={"amount": 10}))

    first_context, _ = sidecar.decisions[0]
    second_context, _ = sidecar.decisions[1]
    assert first_context.history == []
    assert len(second_context.history) == 1
    assert second_context.history[0].tool_name == "look_up_order"
    assert second_context.history[0].status == "ALLOW"
