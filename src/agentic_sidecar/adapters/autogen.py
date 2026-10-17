"""AutoGen Core FunctionTool adapter for plain typed sync/async callables.

Only the returned tools are supervised. Agent construction and model execution
remain owned by AutoGen; a raw callable retained by the host is not isolated.
"""

from collections.abc import Callable, Sequence
from importlib import import_module
from typing import Any

from agentic_sidecar.adapters.langgraph import attach as wrap
from agentic_sidecar.core.sidecar import Sidecar


def attach(sidecar: Sidecar, tools: Sequence[Callable[..., Any]]) -> list[Any]:
    """Build native FunctionTools around governed execution boundaries."""
    sdk = import_module("autogen_core.tools")
    return [
        sdk.FunctionTool(tool, description=tool.__doc__ or tool.__name__)
        for tool in wrap(sidecar, tools)
    ]
