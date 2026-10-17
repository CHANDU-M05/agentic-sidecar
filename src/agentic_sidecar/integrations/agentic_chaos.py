"""Opt-in same-run recovery supervision and gate-failure experiments."""

from collections.abc import Mapping
from typing import Any

from agentic_sidecar import Decision, DecisionContext, Sidecar


def evaluate_recovery(
    sidecar: Sidecar, event: Mapping[str, Any], *, tool_name: str, arguments: dict[str, Any]
) -> Decision:
    """Evaluate/enforce a recovery proposal linked to a native Chaos event.

    Does not execute a tool. Dispatch must still pass through a supported adapter.
    """
    event_id = event.get("id")
    if not isinstance(event_id, str) or not event_id or not event.get("fault_type"):
        raise ValueError("A native Chaos event id and fault_type are required")
    context = DecisionContext(
        tool_name=tool_name,
        tool_args=arguments,
        metadata={"chaos.event_id": event_id, "chaos.fault_type": event["fault_type"]},
    )
    decision = sidecar.evaluate(context)
    return sidecar.enforce(context, decision)
