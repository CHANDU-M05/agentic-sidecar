"""OpenAI Agents FunctionTools; governance exceptions propagate. Hosted tools and handoffs are separate boundaries."""

from collections.abc import Callable, Sequence
from importlib import import_module
from typing import Any

from agentic_sidecar.adapters.callable import attach as wrap
from agentic_sidecar.core.sidecar import Sidecar


def attach(sidecar: Sidecar, tools: Sequence[Callable[..., Any]]) -> list[Any]:
    """Build supervised native SDK tools from plain typed functions."""
    sdk = import_module("agents")
    return [sdk.function_tool(tool, failure_error_function=None) for tool in wrap(sidecar, tools)]
