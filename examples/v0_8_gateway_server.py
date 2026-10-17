"""Separate-process MCP gateway fixture; launched by the integration test.

Production must run the gateway under a separate identity with exclusive access
 to credentials and tools. Stdio peers are trusted launchers, not sandboxed OS users.
"""

import os

from agentic_sidecar.adapters.callable import attach
from agentic_sidecar.intent.alignment import ConstraintBinding
from agentic_sidecar.scopes import GuardrailSpec, ScopedSystem, ScopeLayer


def main() -> None:
    from mcp.server.mcpserver import MCPServer

    server = MCPServer("sidecar-protected-tools")
    config = ScopedSystem(
        system_id="gateway",
        task_id="billing",
        agents=["refund"],
        shared=ScopeLayer(
            guardrails=GuardrailSpec(
                constraints={"limit": 100},
                bindings=[
                    ConstraintBinding(constraint="limit", tool="refund", arg_name="amount"),
                ],
            )
        ),
    )
    agent = config.bind("refund", on_sidecar_failure="fail_closed")

    def refund(amount: int) -> str:
        """Refund through the credential-owning gateway."""
        if not os.environ.get("SIDECAR_DEMO_CREDENTIAL"):
            raise RuntimeError("Gateway credential not configured")
        return f"refunded {amount}"

    (guarded,) = attach(agent.sidecar, [refund])
    server.tool()(guarded)

    @server.tool()
    def audit() -> list[dict]:
        """Task-local test evidence; do not expose broadly in production."""
        return agent.sidecar.runtime.journal.export()

    server.run()


if __name__ == "__main__" and os.environ.get("SIDECAR_RUN_GATEWAY") == "1":
    main()
