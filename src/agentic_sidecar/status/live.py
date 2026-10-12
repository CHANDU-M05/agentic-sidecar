"""Narration of measured runtime state, rather than manually recorded proposals."""

from __future__ import annotations

from typing import Any


def narrate_status(snapshot: dict[str, Any]) -> str:
    """Human-readable objective, action lifecycle, alignment, risk and budget."""
    lines = [
        f"Task: {snapshot['task_id']}",
        f"Objective: {snapshot['objective'] or 'Not supplied'}",
    ]
    state = "STOPPED" if snapshot["stopped"] else "PAUSED" if snapshot["paused"] else "ACTIVE"
    lines.append(f"Status: {state} ({snapshot['mode']})")
    lines.append(f"Risk: {snapshot['risk'] or 'Not evaluated'}")
    alignment = snapshot["alignment"]
    lines.append(f"Intent alignment: {alignment.get('status', 'Not evaluated')}")
    if alignment.get("reason"):
        lines.append(alignment["reason"])
    if snapshot["budget"] is not None:
        budget = snapshot["budget"]
        lines.append(
            f"Budget remaining: ${budget['remaining_cost']:.4f}; "
            f"tokens remaining: {budget['remaining_tokens']}"
        )
    lines.append(f"Executed: {snapshot['executed']}; completed: {snapshot['completed']}")
    for action in snapshot["actions"]:
        lines.append(
            f"{action['state'].upper()}: {action['tool_name']} "
            f"[{action['decision_id']}] — {action['reason']}"
        )
    return "\n".join(lines)
