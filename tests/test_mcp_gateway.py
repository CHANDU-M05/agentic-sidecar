"""Real MCP stdio transport, credential-owning gateway and bypass attempts."""

import asyncio
import os
import sys
from pathlib import Path

import pytest

from agentic_sidecar import Sidecar, SidecarBlockedError
from agentic_sidecar.adapters.mcp import attach
from agentic_sidecar.gate.policy import PolicyAdvisor, PolicyRule


def test_real_mcp_gateway() -> None:
    pytest.importorskip("mcp")
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    async def scenario() -> None:
        parameters = StdioServerParameters(
            command=sys.executable,
            args=[str(Path(__file__).resolve().parents[1] / "examples/v0_8_gateway_server.py")],
            env={
                **os.environ,
                "SIDECAR_RUN_GATEWAY": "1",
                "SIDECAR_DEMO_CREDENTIAL": "gateway-only-fixture",
            },
        )
        async with stdio_client(parameters) as streams, ClientSession(*streams) as session:
            await session.initialize()
            tools = await session.list_tools()
            assert {tool.name for tool in tools.tools} == {"refund", "audit"}
            sidecar = Sidecar(on_sidecar_failure="fail_closed", mode="govern")
            (refund,) = attach(sidecar, session, ["refund"])
            allowed = await refund(amount=10)
            assert not allowed.is_error
            # Direct session bypass still reaches the server's governed boundary.
            denied = await session.call_tool("refund", {"amount": 200})
            assert denied.is_error
            raw = await session.call_tool("raw_refund", {"amount": 10})
            assert raw.is_error
            sidecar.policy = PolicyAdvisor([PolicyRule(tool="refund", effect="deny")])
            with pytest.raises(SidecarBlockedError):
                await refund(amount=10)
            audit = await session.call_tool("audit", {})
            assert not audit.is_error
            assert "gateway-only-fixture" not in str(audit)
            assert "dispatched" in str(audit) or "executed" in str(audit)

    asyncio.run(scenario())
