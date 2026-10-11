"""Exceptions raised by adapters when a Sidecar's Decision Gate blocks a
proposed action in Govern mode (v0.2+).

Not raised by `Sidecar.evaluate()` itself -- a `BLOCK` `Decision` is a
normal outcome, not a Python exception. Turning it into a raised exception
(and thereby actually stopping the call) is each adapter's job at its own
interception point, not core's (AGENTS.md's Package Boundaries: adapters
depend on core, not the reverse -- `core/` has no opinion on what "stopping
a call" means for a given framework).
"""

from __future__ import annotations

from agentic_sidecar.core.context import DecisionContext
from agentic_sidecar.core.decision import Decision


class SidecarBlockedError(RuntimeError):
    """Raised by an adapter (e.g. `agentic_sidecar.adapters.langgraph`) in
    Govern mode when the Decision Gate returns `BLOCK` for a proposed tool
    call, instead of letting the call through. Never raised in Observe
    mode (v0.1's only mode) -- see ROADMAP.md's v0.1/v0.2 scope.
    """

    def __init__(self, decision: Decision, context: DecisionContext) -> None:
        self.decision = decision
        self.context = context
        super().__init__(
            f"Sidecar blocked '{context.tool_name}'({context.tool_args}): {decision.reason}"
        )


class SidecarSuspendedError(RuntimeError):
    """Return control to the caller for PAUSE, ESCALATE, CHALLENGE or REPLAN.

    The proposed tool has not executed. The caller may revise and resubmit it.
    """

    def __init__(self, decision: Decision, context: DecisionContext) -> None:
        self.decision = decision
        self.context = context
        super().__init__(f"Sidecar {decision.status}: {decision.reason}")
