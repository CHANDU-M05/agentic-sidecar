"""Gate remote MCP calls while the MCP SDK owns connectivity and transport."""

from collections.abc import Callable, Sequence
from typing import Any

from agentic_sidecar.adapters.callable import attach as wrap
from agentic_sidecar.core.sidecar import Sidecar


def attach(sidecar: Sidecar, session: Any, tool_names: Sequence[str]) -> list[Callable[..., Any]]:
    """Bind allowlisted remote tools to a real initialized ClientSession.

    Keep the raw session in the trusted harness. Client-side wrapping is advisory
    containment unless the server also enforces its own protected boundary.
    """

    def make_tool(name: str) -> Callable[..., Any]:
        async def remote(**arguments: Any) -> Any:
            return await session.call_tool(name, arguments=arguments)

        remote.__name__ = name
        remote.__doc__ = f"Invoke remote MCP tool {name}."
        return remote

    return wrap(sidecar, [make_tool(name) for name in tool_names])
