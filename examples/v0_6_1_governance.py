"""0.6.1 governance, full-plan review and accounting; offline, no API keys."""

from agentic_sidecar import (
    ApprovalAction,
    ApprovalResponse,
    BudgetGuardian,
    Decision,
    DecisionContext,
    JudgeEvaluator,
    MockJudge,
    PlanEvaluator,
    Sidecar,
    SidecarBlockedError,
    SidecarSuspendedError,
)
from agentic_sidecar.adapters.langgraph import attach


def main() -> None:
    calls: list[str] = []

    def send_notice(message: str) -> str:
        """Send a notice (local demo only)."""
        calls.append(message)
        return message

    sidecar = Sidecar(on_sidecar_failure="fail_closed", mode="govern")

    @sidecar.before_tool_call
    def require_approval(context: DecisionContext) -> Decision:
        return Decision(status="ESCALATE", risk=None, reason="Review notice before sending")

    actions = iter([ApprovalAction.APPROVE_ONCE, ApprovalAction.REJECT])

    @sidecar.on_escalation_required
    def approve(request):
        return ApprovalResponse(request.decision_id, next(actions), explanation="Demo review")

    (send,) = attach(sidecar, [send_notice])
    assert send("first notice") == "first notice"
    try:
        send("second notice")
    except SidecarBlockedError:
        print("Second proposal rejected before dispatch")
    assert calls == ["first notice"]
    assert sidecar.decisions[-1][1].causal_link == sidecar.decisions[-2][1].decision_id

    # Missing approval handler returns control and never calls the tool.
    pending = Sidecar(on_sidecar_failure="fail_closed", mode="govern")
    pending.before_tool_call(require_approval)
    try:
        attach(pending, [send_notice])[0]("pending notice")
    except SidecarSuspendedError as exc:
        assert exc.decision.status == "ESCALATE"
        print("Unresolved proposal suspended:", exc.decision.reason)
    assert calls == ["first notice"]

    reviewer = Sidecar(on_sidecar_failure="fail_closed", roles=["planner"], planner=PlanEvaluator())
    verdict = reviewer.evaluate_plan(
        [{"tool_name": "read_charge"}, {"tool_name": "issue_refund"}],
        goal="Explain the disputed charge",
    )
    assert verdict.status == "REPLAN"
    print("Plan review:", verdict.status)

    budget = BudgetGuardian(max_cost=0.1, max_tokens=20)
    accounting = Sidecar(
        on_sidecar_failure="fail_closed",
        mode="govern",
        roles=["judge", "budget"],
        budget=budget,
        judge=JudgeEvaluator(MockJudge(cost=0.1, tokens=20)),
    )
    verdict = accounting.evaluate(DecisionContext(tool_name="read_order"))
    assert verdict.status == "PAUSE"
    assert budget.current_cost == 0.1 and budget.current_tokens == 20
    print("Judge usage recorded once; task budget:", verdict.status)


if __name__ == "__main__":
    main()
