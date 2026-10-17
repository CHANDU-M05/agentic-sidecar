"""Google ADK FunctionTools. Injected ToolContext arguments are not supported."""

from collections.abc import Callable, Sequence
from importlib import import_module
from typing import Any

from agentic_sidecar.adapters.callable import attach as wrap
from agentic_sidecar.core.sidecar import Sidecar


def attach(sidecar: Sidecar, tools: Sequence[Callable[..., Any]]) -> list[Any]:
    """Build supervised native SDK tools from plain typed functions."""
    sdk = import_module("google.adk.tools")
    return [sdk.FunctionTool(func=tool) for tool in wrap(sidecar, tools)]
