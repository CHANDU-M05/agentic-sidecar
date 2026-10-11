"""Budget, caller-managed approval, and audit types for the 0.6.1 API.

The filename records introduction in 0.4. This example evaluates proposed
calls but dispatches no tools. Application code explicitly constructs an
approval request and invokes its handler; Sidecar registration alone does
not perform this orchestration. No real spend or human input is required.

Run: uv run python examples/v0_4_budget_and_escalation.py
"""

import json
from datetime import datetime, timezone
from uuid import uuid4

from agentic_sidecar import (
    ApprovalAction,
    ApprovalResponse,
    AuditRecord,
    BudgetGuardian,
    CausalLink,
    Decision,
    DecisionContext,
    DecisionRationale,
    DecisionTrigger,
    EscalationHandler,
    EscalationRequest,
    Sidecar,
)


class DemoApprovalHandler(EscalationHandler):
    """Simulate a human rejection; application code invokes this handler."""

    def handle_escalation(self, request: EscalationRequest) -> ApprovalResponse:
        return ApprovalResponse(
            decision_id=request.decision_id,
            action=ApprovalAction.REJECT,
            explanation="Keep this demonstration within its configured budget",
        )


def demo_budget_guardian() -> None:
    budget = BudgetGuardian(max_cost=2, max_tokens=2000)
    sidecar = Sidecar(
        on_sidecar_failure="fail_closed",
        budget=budget,
        roles=["policy", "risk", "budget"],
    )
    budget.record_invocation(cost=0.50, tokens=500)
    verdict = sidecar.evaluate(DecisionContext(tool_name="read_order"))
    assert verdict.status == "ALLOW"
    print("Within recorded budget:", verdict.status)

    budget.record_invocation(cost=1.50, tokens=1500)
    context = DecisionContext(tool_name="issue_refund", tool_args={"amount": 100})
    verdict = sidecar.evaluate(context)
    assert verdict.status == "PAUSE" and verdict.escalation_required
    print("At recorded ceiling:", verdict.status)

    # Caller-managed approval: no tool is dispatched while handling this proposal.
    request = EscalationRequest(
        decision_id=str(uuid4()),
        reason=verdict.reason,
        context={"tool_name": context.tool_name, "arguments": context.tool_args},
        available_actions=[ApprovalAction.APPROVE_ONCE, ApprovalAction.REJECT],
    )
    response = DemoApprovalHandler().handle_escalation(request)
    assert response.decision_id == request.decision_id
    assert response.action == ApprovalAction.REJECT
    print("Simulated human response:", response.action.value)
    print("Caller leaves the proposed action undispatched.")

    # Serialize the proposal and its caller-managed resolution with a causal link.
    proposal = AuditRecord(
        decision_id=request.decision_id,
        timestamp=datetime.now(timezone.utc),
        outcome="PAUSE",
        trigger=DecisionTrigger("tool_call", context.tool_name, context.tool_args),
        rationale=DecisionRationale(budget_findings=[verdict.reason], reason=verdict.reason),
    )
    resolution = AuditRecord(
        decision_id=str(uuid4()),
        timestamp=datetime.now(timezone.utc),
        outcome="BLOCK",
        trigger=proposal.trigger,
        rationale=DecisionRationale(reason=response.explanation),
        causal_link=CausalLink(parent_decision_id=request.decision_id),
        execution_context={"approval_action": response.action.value},
    )
    print(json.dumps([proposal.to_dict(), resolution.to_dict()], indent=2))


def demo_decision_outcomes() -> None:
    """Show the seven supported result types, separate from execution behavior."""
    for status in ("ALLOW", "WARN", "BLOCK", "CHALLENGE", "REPLAN", "PAUSE", "ESCALATE"):
        decision = Decision(
            status=status,
            risk="LOW",
            reason="Illustrative result type",
            escalation_required=status in ("PAUSE", "ESCALATE"),
        )
        print("Outcome type:", decision.status)


if __name__ == "__main__":
    demo_budget_guardian()
    demo_decision_outcomes()
