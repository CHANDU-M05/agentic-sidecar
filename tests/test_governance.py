"""Executable governance contracts, including real LangGraph tool dispatch."""

import asyncio

import pytest

from agentic_sidecar import (
    ApprovalAction,
    ApprovalResponse,
    Decision,
    DecisionContext,
    Sidecar,
    SidecarBlockedError,
    SidecarSuspendedError,
)
from agentic_sidecar.adapters.langgraph import attach
from agentic_sidecar.intent import IntentEnvelope, IntentGuardian

STATUSES = ["ALLOW", "WARN", "BLOCK", "PAUSE", "ESCALATE", "CHALLENGE", "REPLAN"]


def configured(status, *, mode="govern", failure="fail_closed"):
    sidecar = Sidecar(on_sidecar_failure=failure, mode=mode)
    sidecar.before_tool_call(lambda context: Decision(status=status, risk=None, reason="fixture"))
    return sidecar


@pytest.mark.parametrize("status", STATUSES)
@pytest.mark.parametrize("mode", ["observe", "govern"])
@pytest.mark.parametrize("asynchronous", [False, True])
def test_outcome_controls_dispatch(status, mode, asynchronous):
    calls = []

    def read(value: int) -> int:
        """Read a value."""
        calls.append(value)
        return value

    async def async_read(value: int) -> int:
        """Read a value asynchronously."""
        return read(value)

    sidecar = configured(status, mode=mode)
    wrapped = attach(sidecar, [async_read if asynchronous else read])[0]

    def invoke():
        return asyncio.run(wrapped(7)) if asynchronous else wrapped(7)

    if mode == "observe" or status in ("ALLOW", "WARN"):
        assert invoke() == 7
        assert calls == [7]
    else:
        exception = SidecarBlockedError if status == "BLOCK" else SidecarSuspendedError
        with pytest.raises(exception) as error:
            invoke()
        assert error.value.decision.status == status
        assert calls == []


@pytest.mark.parametrize("action", list(ApprovalAction))
def test_approval_resolution_and_one_invocation(action):
    sidecar = configured("PAUSE")
    if action == ApprovalAction.MODIFY_INTENT:
        sidecar.roles = ("intent_guardian",)
        envelope = IntentEnvelope(goal="old", requested_by={"type": "human", "id": "u"})
        sidecar.set_intent(IntentGuardian(envelope))
    requests = []

    @sidecar.on_escalation_required
    def handler(request):
        requests.append(request)
        return ApprovalResponse(
            request.decision_id,
            action,
            modified_intent={"goal": "new", "requested_by": {"type": "human", "id": "u"}},
        )

    calls = []

    def read():
        calls.append(1)
        return "done"

    wrapped = attach(sidecar, [read])[0]
    if action == ApprovalAction.APPROVE_ONCE:
        assert wrapped() == "done"
        assert wrapped() == "done"
        assert len(requests) == 2
        assert requests[0].decision_id != requests[1].decision_id
        assert len(calls) == 2
        assert sidecar.decisions[-1][1].causal_link == requests[-1].decision_id
    else:
        error = (
            SidecarBlockedError
            if action in (ApprovalAction.REJECT, ApprovalAction.STOP_AGENT)
            else SidecarSuspendedError
        )
        with pytest.raises(error):
            wrapped()
        assert calls == []
        if action == ApprovalAction.MODIFY_INTENT:
            assert sidecar.intent.envelope.goal == "new"
        if action == ApprovalAction.STOP_AGENT:
            with pytest.raises(SidecarBlockedError):
                wrapped()
            assert len(requests) == 1


@pytest.mark.parametrize("failure,expected", [("fail_closed", "BLOCK"), ("fail_open", "ALLOW")])
@pytest.mark.parametrize("bad", ["id", "type", "action", "exception", "intent"])
def test_malformed_approvals_follow_failure_policy(failure, expected, bad):
    sidecar = configured("ESCALATE", failure=failure)

    @sidecar.on_escalation_required
    def handler(request):
        if bad == "exception":
            raise RuntimeError("unavailable")
        if bad == "type":
            return None
        if bad == "intent":
            return ApprovalResponse(request.decision_id, ApprovalAction.MODIFY_INTENT)
        return ApprovalResponse(
            "wrong" if bad == "id" else request.decision_id,
            "invalid" if bad == "action" else ApprovalAction.APPROVE_ONCE,
        )

    context = DecisionContext(tool_name="read")
    decision = sidecar._resolve_approval(context, sidecar.evaluate(context))
    assert decision.status == expected


@pytest.mark.parametrize("failure,expected", [("fail_closed", "BLOCK"), ("fail_open", "ALLOW")])
@pytest.mark.parametrize("stage", ["injection", "hook", "recording"])
def test_whole_evaluation_boundary_failure(failure, expected, stage, monkeypatch):
    sidecar = Sidecar(on_sidecar_failure=failure)

    def broken(*args):
        if stage == "hook":
            return {"status": "ALLOW"}
        raise RuntimeError("unavailable")

    if stage == "hook":
        sidecar.before_tool_call(broken)
    else:
        monkeypatch.setattr(sidecar, "_inject" if stage == "injection" else "_record", broken)
    assert sidecar.evaluate(DecisionContext(tool_name="read")).status == expected


def test_history_is_snapshot():
    sidecar = Sidecar(on_sidecar_failure="fail_closed")
    context = DecisionContext(tool_name="read", tool_args={"nested": {"value": 1}})
    sidecar.evaluate(context)
    context.tool_args["nested"]["value"] = 2
    sidecar.evaluate(context)
    assert sidecar.decisions[0][0].tool_args["nested"]["value"] == 1
    assert context.history[0].tool_args["nested"]["value"] == 1


@pytest.mark.parametrize("status", STATUSES)
def test_real_langgraph_dispatch(status):
    langgraph = pytest.importorskip("langgraph.prebuilt")
    from langchain_core.messages import AIMessage
    from langgraph.graph import END, START, MessagesState, StateGraph

    calls = []

    def read(value: int) -> int:
        """Read a value."""
        calls.append(value)
        return value

    node = langgraph.ToolNode(attach(configured(status), [read]), handle_tool_errors=False)
    builder = StateGraph(MessagesState)
    builder.add_node("tools", node)
    builder.add_edge(START, "tools")
    builder.add_edge("tools", END)
    graph = builder.compile()
    message = AIMessage(content="", tool_calls=[{"name": "read", "args": {"value": 7}, "id": "t"}])
    if status in ("ALLOW", "WARN"):
        result = graph.invoke({"messages": [message]})
        assert result["messages"][-1].content == "7"
        assert calls == [7]
    else:
        with pytest.raises(SidecarBlockedError if status == "BLOCK" else SidecarSuspendedError):
            graph.invoke({"messages": [message]})
        assert calls == []


def test_reused_hook_decision_gets_fresh_approval_ids():
    sidecar = Sidecar(on_sidecar_failure="fail_closed", mode="govern")
    verdict = Decision(status="PAUSE", risk=None, reason="review")
    sidecar.before_tool_call(lambda context: verdict)
    first = sidecar.evaluate(DecisionContext(tool_name="read"))
    second = sidecar.evaluate(DecisionContext(tool_name="read"))
    assert first.decision_id != second.decision_id


def test_modified_intent_reevaluation_links_to_approval_origin():
    sidecar = configured("PAUSE")
    sidecar.roles = ("intent_guardian",)
    sidecar.set_intent(IntentGuardian(IntentEnvelope(goal="old", requested_by={"id": "u"})))

    @sidecar.on_escalation_required
    def handler(request):
        return ApprovalResponse(
            request.decision_id,
            ApprovalAction.MODIFY_INTENT,
            modified_intent={"goal": "new", "requested_by": {"id": "u"}},
        )

    context = DecisionContext(tool_name="read")
    proposal = sidecar.evaluate(context)
    with pytest.raises(SidecarSuspendedError) as error:
        sidecar.enforce(context, proposal)
    assert error.value.decision.causal_link == proposal.decision_id
    assert sidecar.decisions[-1][1].causal_link == proposal.decision_id


def test_stale_response_cannot_approve_a_new_proposal():
    sidecar = configured("PAUSE")
    old = sidecar.evaluate(DecisionContext(tool_name="read"))
    sidecar.on_escalation_required(
        lambda request: ApprovalResponse(old.decision_id, ApprovalAction.APPROVE_ONCE)
    )
    context = DecisionContext(tool_name="read")
    with pytest.raises(SidecarBlockedError):
        sidecar.enforce(context, sidecar.evaluate(context))


def test_registered_handler_precedes_hook():
    from agentic_sidecar import EscalationHandler

    requests = []

    class Handler(EscalationHandler):
        def handle_escalation(self, request):
            requests.append(request)
            return ApprovalResponse(request.decision_id, ApprovalAction.APPROVE_ONCE)

    sidecar = configured("ESCALATE")
    sidecar.escalation_handler = Handler()
    sidecar.on_escalation_required(lambda request: None)
    context = DecisionContext(tool_name="read", tool_args={"id": 7})
    result = sidecar.enforce(context, sidecar.evaluate(context))
    assert result.status == "ALLOW"
    assert requests[0].context["tool_args"] == {"id": 7}
