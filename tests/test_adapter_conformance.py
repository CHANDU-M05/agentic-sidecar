"""Identical verdicts through native SDK dispatch without model credentials."""

import asyncio
import importlib
import json
from typing import Any

import pytest

from agentic_sidecar import Decision, Sidecar, SidecarBlockedError, SidecarSuspendedError
from agentic_sidecar.gate.escalation import ApprovalAction, ApprovalResponse

SDK_MODULES = {
    "langgraph": "langchain_core",
    "autogen": "autogen_core",
    "crewai": "crewai",
    "openai_agents": "agents",
    "google_adk": "google.adk.tools",
}


def dispatch(adapter: str, sidecar: Sidecar, tool: Any, *, asynchronous: bool = False) -> Any:
    pytest.importorskip(SDK_MODULES[adapter])
    module = importlib.import_module(f"agentic_sidecar.adapters.{adapter}")
    (wrapped,) = module.attach(sidecar, [tool])
    if adapter == "langgraph":
        from langchain_core.tools import StructuredTool

        native = StructuredTool.from_function(
            func=None if asynchronous else wrapped,
            coroutine=wrapped if asynchronous else None,
        )
        return (
            asyncio.run(native.ainvoke({"amount": 10}))
            if asynchronous
            else native.invoke({"amount": 10})
        )
    if adapter == "autogen":
        from autogen_core import CancellationToken

        return asyncio.run(wrapped.run_json({"amount": 10}, CancellationToken()))
    if adapter == "crewai":
        return wrapped.run(amount=10)
    if adapter == "openai_agents":
        from agents.tool_context import ToolContext

        return asyncio.run(
            wrapped.on_invoke_tool(
                ToolContext(
                    context=None,
                    tool_name=wrapped.name,
                    tool_call_id="call-1",
                    tool_arguments=json.dumps({"amount": 10}),
                ),
                json.dumps({"amount": 10}),
            )
        )
    return asyncio.run(wrapped.run_async(args={"amount": 10}, tool_context=None))


@pytest.mark.parametrize("adapter", SDK_MODULES)
@pytest.mark.parametrize("asynchronous", [False, True])
@pytest.mark.parametrize("mode", ["observe", "govern"])
@pytest.mark.parametrize(
    "status", ["ALLOW", "WARN", "BLOCK", "PAUSE", "ESCALATE", "CHALLENGE", "REPLAN"]
)
def test_outcome_conformance(adapter: str, asynchronous: bool, mode: Any, status: Any) -> None:
    calls: list[int] = []

    def refund(amount: int) -> str:
        """Refund a customer."""
        calls.append(amount)
        return "refunded"

    async def async_refund(amount: int) -> str:
        """Refund a customer asynchronously."""
        return refund(amount)

    sidecar = Sidecar(on_sidecar_failure="fail_closed", mode=mode)
    sidecar.before_tool_call(lambda _: Decision(status=status, risk="LOW", reason="fixture"))
    should_run = mode == "observe" or status in ("ALLOW", "WARN")
    if should_run:
        assert (
            dispatch(
                adapter,
                sidecar,
                async_refund if asynchronous else refund,
                asynchronous=asynchronous,
            )
            == "refunded"
        )
    else:
        error = SidecarBlockedError if status == "BLOCK" else SidecarSuspendedError
        with pytest.raises(error):
            dispatch(
                adapter,
                sidecar,
                async_refund if asynchronous else refund,
                asynchronous=asynchronous,
            )
    assert calls == ([10] if should_run else [])


@pytest.mark.parametrize("adapter", SDK_MODULES)
@pytest.mark.parametrize("failure", ["fail_open", "fail_closed"])
def test_failure_conformance(adapter: str, failure: Any) -> None:
    sidecar = Sidecar(on_sidecar_failure=failure, mode="govern")

    def broken(_: Any) -> Decision:
        raise TimeoutError("gate unavailable")

    sidecar.before_tool_call(broken)

    def read(amount: int) -> str:
        """Read an amount."""
        return "read"

    if failure == "fail_open":
        assert dispatch(adapter, sidecar, read) == "read"
    else:
        with pytest.raises(SidecarBlockedError):
            dispatch(adapter, sidecar, read)


@pytest.mark.parametrize("adapter", SDK_MODULES)
def test_approval_conformance(adapter: str) -> None:
    sidecar = Sidecar(on_sidecar_failure="fail_closed", mode="govern")
    sidecar.on_escalation_required(
        lambda request: ApprovalResponse(
            decision_id=request.decision_id,
            action=ApprovalAction.APPROVE_ONCE,
        )
    )
    sidecar.before_tool_call(lambda _: Decision(status="PAUSE", risk="LOW", reason="approval"))

    def read(amount: int) -> str:
        """Read an amount."""
        return "approved"

    assert dispatch(adapter, sidecar, read) == "approved"
