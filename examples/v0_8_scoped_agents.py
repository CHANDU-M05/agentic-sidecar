"""Shared context/guardrails plus exclusive agent context and restrictions."""

from agentic_sidecar import (
    ContextSpec,
    GuardrailSpec,
    ScopedSystem,
    ScopeLayer,
    SidecarBlockedError,
)
from agentic_sidecar.adapters.langgraph import attach
from agentic_sidecar.gate.policy import PolicyRule


def main() -> None:
    system = ScopedSystem(
        system_id="support",
        task_id="ticket-42",
        agents=["research", "refund"],
        shared=ScopeLayer(
            context=ContextSpec(goal="Resolve this billing issue", values={"customer": "A100"}),
            guardrails=GuardrailSpec(rules=[PolicyRule(tool="delete_*", effect="deny")]),
        ),
        exclusive={
            "research": ScopeLayer(
                context=ContextSpec(values={"investigation": "Check duplicate charges"})
            ),
            "refund": ScopeLayer(
                context=ContextSpec(goal="Prepare the refund", values={"transaction": "T100"}),
                guardrails=GuardrailSpec(rules=[PolicyRule(tool="export_*", effect="deny")]),
            ),
        },
    )
    research = system.bind("research", on_sidecar_failure="fail_closed")
    refund = system.bind("refund", on_sidecar_failure="fail_closed")
    # The trusted host puts this payload in the agent's instructions/memory.
    instructions: list[dict] = []
    refund.deliver(instructions.append)
    assert "investigation" not in instructions[0]["values"]
    assert "transaction" not in research.context()["values"]

    def export_records() -> str:
        """Export customer records."""
        return "exported"

    (guarded,) = attach(refund.sidecar, [export_records])
    try:
        guarded()
    except SidecarBlockedError:
        print("Refund agent export blocked; shared context delivered with exclusive task context.")
    else:
        raise AssertionError("Exclusive guardrail did not block")


if __name__ == "__main__":
    main()
