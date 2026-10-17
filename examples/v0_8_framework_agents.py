"""Two host-bound agents using different native SDK tool surfaces, offline."""

import asyncio
from importlib.util import find_spec

from agentic_sidecar import (
    ContextSpec,
    GuardrailSpec,
    ScopedSystem,
    ScopeLayer,
    SidecarBlockedError,
)
from agentic_sidecar.gate.policy import PolicyRule


def main() -> None:
    if find_spec("autogen_core") is None or find_spec("langchain_core") is None:
        print("Install agentic-sidecar[autogen,langgraph] to run the cross-framework example.")
        return
    from autogen_core import CancellationToken
    from langchain_core.tools import StructuredTool

    from agentic_sidecar.adapters.autogen import attach as autogen_tools
    from agentic_sidecar.adapters.langgraph import attach as langgraph_tools

    config = ScopedSystem(
        system_id="support",
        task_id="ticket",
        agents=["research", "refund"],
        shared=ScopeLayer(
            context=ContextSpec(goal="Resolve billing"),
            guardrails=GuardrailSpec(rules=[PolicyRule(tool="delete_*", effect="deny")]),
        ),
        exclusive={"refund": ScopeLayer(context=ContextSpec(values={"transaction": "T100"}))},
    )
    research = config.bind("research", on_sidecar_failure="fail_closed")
    refund = config.bind("refund", on_sidecar_failure="fail_closed")

    def read_order(order_id: str) -> str:
        """Read the order."""
        return order_id

    def delete_order(order_id: str) -> str:
        """Delete the order."""
        raise AssertionError("A shared denial must stop this function")

    (read,) = langgraph_tools(research.sidecar, [read_order])
    assert StructuredTool.from_function(read).invoke({"order_id": "A100"}) == "A100"
    (delete,) = autogen_tools(refund.sidecar, [delete_order])
    try:
        asyncio.run(delete.run_json({"order_id": "A100"}, CancellationToken()))
    except SidecarBlockedError:
        print("LangGraph research completed; AutoGen refund respected the shared denial.")
    else:
        raise AssertionError("Expected a shared guardrail denial")
    assert "transaction" not in research.context()["values"]
    assert refund.context()["values"]["transaction"] == "T100"


if __name__ == "__main__":
    main()
