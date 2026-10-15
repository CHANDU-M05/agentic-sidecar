"""Interactive approval handler for an attached Sidecar; no remote runtime required."""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from rich.console import Console
from rich.prompt import Prompt

from agentic_sidecar.gate.escalation import (
    ApprovalAction,
    ApprovalResponse,
    EscalationHandler,
    EscalationRequest,
)


@dataclass
class CLIApprovalHandler(EscalationHandler):
    """Prompt locally for the response to one PAUSE/ESCALATE decision.

    EOF, malformed JSON and terminal errors propagate through Sidecar's failure policy.
    MODIFY_INTENT accepts a complete IntentEnvelope JSON object and reevaluates.
    """

    console: Console = field(default_factory=Console)

    def handle_escalation(self, request: EscalationRequest) -> ApprovalResponse:
        self.console.print(f"Decision {request.decision_id}: {request.reason}", markup=False)
        self.console.print_json(data=request.context)
        action = ApprovalAction(
            Prompt.ask(
                "Action",
                console=self.console,
                choices=[action.value for action in request.available_actions],
                default=ApprovalAction.REJECT.value,
            )
        )
        modified_intent = None
        if action == ApprovalAction.MODIFY_INTENT:
            value = json.loads(Prompt.ask("Complete IntentEnvelope JSON", console=self.console))
            if not isinstance(value, dict):
                raise ValueError("IntentEnvelope JSON must be an object")
            modified_intent = value
        explanation = Prompt.ask("Explanation (optional)", console=self.console, default="")
        return ApprovalResponse(request.decision_id, action, modified_intent, explanation)
