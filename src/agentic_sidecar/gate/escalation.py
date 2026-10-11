"""Human-in-the-loop escalation flow for PAUSE and ESCALATE outcomes.

Provides structured request/response types for pausing execution and requesting
human approval on consequential decisions. Govern invokes registered handlers;
CLIApprovalHandler provides a local prompt. Runtime-connected operator UI is v0.7.

See concept.md §16 for the use case walkthrough.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ApprovalAction(str, Enum):
    """Human response options when an action is escalated for approval."""

    APPROVE_ONCE = "approve_once"
    REJECT = "reject"
    MODIFY_INTENT = "modify_intent"
    ASK_AGENT_TO_REPLAN = "ask_agent_to_replan"
    STOP_AGENT = "stop_agent"


@dataclass
class EscalationRequest:
    """A request to pause execution and ask a human for guidance.

    Attributes:
        decision_id: Unique identifier for this escalation.
        reason: Why execution is paused (e.g. "PAUSE: refund exceeds
            authorized limit").
        context: Details about the proposed action (tool name, arguments,
            intent violation).
        available_actions: Which ApprovalActions the human can choose.
    """

    decision_id: str
    reason: str
    context: dict[str, Any]
    available_actions: list[ApprovalAction]


@dataclass
class ApprovalResponse:
    """A human's response to an EscalationRequest.

    Attributes:
        decision_id: Correlates back to the EscalationRequest.
        action: Which ApprovalAction the human chose.
        modified_intent: If action==MODIFY_INTENT, the new intent (as dict).
        explanation: Optional notes from the human.
    """

    decision_id: str
    action: ApprovalAction
    modified_intent: dict[str, Any] | None = None
    explanation: str = ""


@dataclass
class EscalationHandler:
    """Handles paused decisions and collects human approval.

    Implement handle_escalation, register an on_escalation_required hook,
    or use agentic_sidecar.cli.approval.CLIApprovalHandler. The base interface
    raises NotImplementedError. Govern invokes handlers for PAUSE/ESCALATE.
    """

    def handle_escalation(self, request: EscalationRequest) -> ApprovalResponse:
        """Pause execution and request human guidance.

        Args:
            request: The EscalationRequest with details and available actions.

        Returns:
            ApprovalResponse with the human's decision.

        Raises:
            NotImplementedError: In the default (no handler registered).
        """
        raise NotImplementedError(
            "No EscalationHandler registered. Register one via "
            "@sidecar.on_escalation_required or pass escalation_handler= "
            "to Sidecar.__init__. Use agentic_sidecar.cli.approval.CLIApprovalHandler "
            "for a local prompt."
        )
