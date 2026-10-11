"""`DecisionContext` -- what gets passed to every evaluator (Policy, Risk,
and, from v0.2, Intent Guardian) at a decision boundary.

`DecisionContext` itself carries only a lightweight `IntentSnapshot`, not
the full `IntentEnvelope` (that lives in `agentic_sidecar.intent.envelope`,
which `core/` does not depend on -- see `IntentEnvelope.to_snapshot()`).
This matches concept.md §7, Intent Injection: only the relevant intent
needs to reach each decision boundary, not the whole envelope. `metadata`
remains the escape hatch for anything a custom `@sidecar.before_tool_call`
hook or future evaluator wants to attach without a breaking change here.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from agentic_sidecar.core.decision import DecisionStatus


class IntentSnapshot(BaseModel):
    """A lightweight, decision-time view of the active `IntentEnvelope` --
    goal and constraints only. `Sidecar.evaluate()` builds this from
    `IntentEnvelope.to_snapshot()`; it is not something callers construct
    directly.
    """

    goal: str
    constraints: dict[str, Any] = Field(default_factory=dict)


class HistoryEntry(BaseModel):
    """One prior decision in this Sidecar's evaluation history.
    `Sidecar.evaluate()` populates `DecisionContext.history` from its own
    `self.decisions` log before dispatching to an evaluator -- also not
    something callers build directly.
    """

    tool_name: str
    tool_args: dict[str, Any] = Field(default_factory=dict)
    status: DecisionStatus


class DecisionContext(BaseModel):
    """The proposed action being evaluated at a decision boundary.

    `tool_name` and `tool_args` describe the tool call itself (see
    concept.md §14's decision boundaries -- v0.1 only intercepts tool
    invocation). `intent` and `history` are injected by `Sidecar.evaluate()`
    itself, not by the caller constructing the context -- an adapter (e.g.
    `agentic_sidecar.adapters.langgraph`) only needs to supply `tool_name`
    and `tool_args`.

    Deliberately *not* frozen (unlike `Decision`): `Sidecar.evaluate()`
    injects `intent`/`history` by mutating the instance the caller passed
    in, in place, so that caller's own reference reflects the fully
    evaluated context once `evaluate()` returns -- e.g. an adapter building
    `SidecarBlockedError` after the call gets the context Intent Guardian
    actually saw, not the bare one it originally constructed.
    """

    tool_name: str
    tool_args: dict[str, Any] = Field(default_factory=dict)
    intent: IntentSnapshot | None = None
    history: list[HistoryEntry] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    boundary: Literal["tool_call", "plan"] = "tool_call"
    goal: str = ""
    plan: list[dict[str, Any]] = Field(default_factory=list)
