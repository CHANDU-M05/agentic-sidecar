"""CrewAI native tools over the shared execution boundary."""

import inspect
from collections.abc import Callable, Sequence
from importlib import import_module
from typing import Any, get_type_hints

from pydantic import create_model

from agentic_sidecar.adapters.callable import attach as wrap
from agentic_sidecar.core.sidecar import Sidecar


def attach(sidecar: Sidecar, tools: Sequence[Callable[..., Any]]) -> list[Any]:
    """Build native tools with argument defaults preserved in the SDK schema."""
    sdk = import_module("crewai.tools.base_tool")
    native = []
    for original, tool in zip(tools, wrap(sidecar, tools), strict=True):
        hints = get_type_hints(original)
        fields: dict[str, Any] = {}
        for name, parameter in inspect.signature(original).parameters.items():
            if parameter.kind in (
                parameter.VAR_POSITIONAL,
                parameter.VAR_KEYWORD,
                parameter.POSITIONAL_ONLY,
            ):
                raise ValueError("CrewAI requires named tool arguments")
            fields[name] = (
                hints.get(name, Any),
                ... if parameter.default is parameter.empty else parameter.default,
            )
        schema = create_model(f"{original.__name__}Arguments", **fields)
        native.append(
            sdk.Tool(
                name=original.__name__,
                description=original.__doc__ or original.__name__,
                func=tool,
                args_schema=schema,
            )
        )
    return native
