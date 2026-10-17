"""Scope composition, explicit context transport, and governed bypass checks."""

from typing import Any

import pytest

from agentic_sidecar import Decision, DecisionContext, SidecarBlockedError
from agentic_sidecar.adapters.callable import attach
from agentic_sidecar.gate.policy import PolicyRule
from agentic_sidecar.intent.alignment import ConstraintBinding
from agentic_sidecar.scopes import ContextSpec, GuardrailSpec, ScopedSystem, ScopeLayer


def system(**kwargs: Any) -> ScopedSystem:
    return ScopedSystem(
        system_id="billing", task_id="ticket-1", agents=["research", "refund"], **kwargs
    )


def test_exclusive_context_delivery_and_copies() -> None:
    config = system(
        shared=ScopeLayer(context=ContextSpec(goal="Resolve billing", values={"customer": "A"})),
        exclusive={
            "refund": ScopeLayer(context=ContextSpec(goal="Refund", values={"secret": [42]}))
        },
    )
    research = config.bind("research", on_sidecar_failure="fail_closed")
    refund = config.bind("refund", on_sidecar_failure="fail_closed")
    assert research.context()["values"] == {"customer": "A"}
    received = []
    refund.deliver(received.append)
    received[0]["values"]["secret"].append(100)
    assert refund.context()["values"]["secret"] == [42]
    context = DecisionContext(tool_name="read", metadata={"sidecar.scope": {"agent_id": "spoof"}})
    research.sidecar.evaluate(context)
    assert context.metadata["sidecar.scope"]["agent_id"] == "research"
    assert "secret" not in context.metadata["sidecar.context"]
    assert refund.sidecar.decisions == []


def test_shared_deny_cannot_be_weakened_by_exclusive_allow_or_hook() -> None:
    config = system(
        shared=ScopeLayer(
            guardrails=GuardrailSpec(rules=[PolicyRule(tool="delete", effect="deny")])
        ),
        exclusive={
            "refund": ScopeLayer(
                guardrails=GuardrailSpec(rules=[PolicyRule(tool="*", effect="allow")])
            )
        },
    )
    agent = config.bind("refund", on_sidecar_failure="fail_closed")
    agent.sidecar.before_tool_call(
        lambda _: Decision(status="ALLOW", risk="LOW", reason="override")
    )
    calls = []

    def delete() -> None:
        """Delete a record."""
        calls.append(1)

    (guarded,) = attach(agent.sidecar, [delete])
    with pytest.raises(SidecarBlockedError):
        guarded()
    assert calls == []


def test_independent_constraint_layers_and_plan_checks() -> None:
    binding = ConstraintBinding(constraint="limit", tool="refund", arg_name="amount")
    config = system(
        shared=ScopeLayer(guardrails=GuardrailSpec(constraints={"limit": 100}, bindings=[binding])),
        exclusive={
            "refund": ScopeLayer(
                guardrails=GuardrailSpec(constraints={"limit": 200}, bindings=[binding])
            )
        },
    )
    agent = config.bind("refund", on_sidecar_failure="fail_closed")
    assert (
        agent.sidecar.evaluate(
            DecisionContext(tool_name="refund", tool_args={"amount": 150})
        ).status
        == "BLOCK"
    )
    assert agent.sidecar.evaluate(DecisionContext(tool_name="refund")).status == "BLOCK"
    assert (
        agent.sidecar.evaluate_plan([{"tool_name": "refund", "arguments": {"amount": 150}}]).status
        == "BLOCK"
    )


@pytest.mark.parametrize("context", [False, True])
@pytest.mark.parametrize("guardrails", [False, True])
@pytest.mark.parametrize("shared", [False, True])
def test_independent_configuration_combinations(
    context: bool, guardrails: bool, shared: bool
) -> None:
    layer = ScopeLayer(
        context=ContextSpec(goal="help") if context else None,
        guardrails=GuardrailSpec(rules=[PolicyRule(tool="delete", effect="deny")])
        if guardrails
        else None,
    )
    config = system(shared=layer if shared else None, exclusive={} if shared else {"refund": layer})
    refund = config.bind("refund", on_sidecar_failure="fail_closed")
    research = config.bind("research", on_sidecar_failure="fail_closed")
    assert bool(refund.context()["goals"]) == context
    assert bool(research.context()["goals"]) == (context and shared)
    assert (
        refund.sidecar.evaluate(DecisionContext(tool_name="delete")).status == "BLOCK"
    ) == guardrails
    assert (research.sidecar.evaluate(DecisionContext(tool_name="delete")).status == "BLOCK") == (
        guardrails and shared
    )


def test_invalid_scope_and_context_conflict() -> None:
    with pytest.raises(ValueError, match="unknown"):
        system(exclusive={"unknown": ScopeLayer()})
    with pytest.raises(ValueError, match="Unknown"):
        system().bind("unknown", on_sidecar_failure="fail_closed")
    with pytest.raises(ValueError, match="Conflicting"):
        system(
            shared=ScopeLayer(context=ContextSpec(values={"env": "prod"})),
            exclusive={"refund": ScopeLayer(context=ContextSpec(values={"env": "test"}))},
        )
    with pytest.raises(ValueError, match="constraint"):
        system(
            shared=ScopeLayer(
                guardrails=GuardrailSpec(
                    bindings=[ConstraintBinding(constraint="missing", tool="*", arg_name="x")]
                )
            )
        )


def test_warning_does_not_skip_later_denial() -> None:
    config = system(
        shared=ScopeLayer(
            guardrails=GuardrailSpec(
                constraints={"limit": 10},
                bindings=[
                    ConstraintBinding(
                        constraint="limit", tool="refund", arg_name="amount", severity="WARN"
                    )
                ],
            )
        ),
        exclusive={
            "refund": ScopeLayer(
                guardrails=GuardrailSpec(rules=[PolicyRule(tool="refund", effect="deny")])
            )
        },
    )
    agent = config.bind("refund", on_sidecar_failure="fail_closed")
    assert (
        agent.sidecar.evaluate(DecisionContext(tool_name="refund", tool_args={"amount": 20})).status
        == "BLOCK"
    )


def test_all_mandatory_checks_run_before_approval_resolution() -> None:
    from agentic_sidecar import Sidecar

    sidecar = Sidecar(
        on_sidecar_failure="fail_closed",
        mode="govern",
        mandatory_checks=[
            lambda _: Decision(status="PAUSE", risk="LOW", reason="approval"),
            lambda _: Decision(status="BLOCK", risk="LOW", reason="mandatory denial"),
        ],
    )
    assert sidecar.evaluate(DecisionContext(tool_name="read")).status == "BLOCK"


def test_scoped_guardrails_are_part_of_audit_policy_fingerprint() -> None:
    fingerprints = []
    for effect in ["allow", "deny"]:
        config = system(
            shared=ScopeLayer(
                guardrails=GuardrailSpec(rules=[PolicyRule(tool="read", effect=effect)])
            )
        )
        bound = config.bind("research", on_sidecar_failure="fail_closed")
        bound.sidecar.evaluate(DecisionContext(tool_name="read"))
        event = next(e for e in bound.sidecar.runtime.journal.export() if e["kind"] == "decision")
        assert event["payload"]["policy"]["mandatory"]["shared"]["guardrails"]["rules"]
        fingerprints.append(event["payload"]["policy_version"])
    assert len(set(fingerprints)) == 2


def test_positional_only_binding_cannot_be_overwritten_by_extra_keywords() -> None:
    config = system(
        shared=ScopeLayer(
            guardrails=GuardrailSpec(
                constraints={"limit": 100},
                bindings=[ConstraintBinding(constraint="limit", tool="refund", arg_name="amount")],
            )
        )
    )
    bound = config.bind("refund", on_sidecar_failure="fail_closed")
    calls = []

    def refund(amount: int, /, **metadata: object) -> int:
        """Refund the positional amount."""
        calls.append((amount, metadata))
        return amount

    (guarded,) = attach(bound.sidecar, [refund])
    with pytest.raises(SidecarBlockedError):
        guarded(200, amount=10)
    assert calls == []
    assert guarded(50, amount=10) == 50
    context, _ = bound.sidecar.decisions[-1]
    assert context.tool_args == {"amount": 50, "metadata": {"amount": 10}}
    assert calls == [(50, {"amount": 10})]

