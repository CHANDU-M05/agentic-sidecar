"""Shared sync/async callable execution boundary for framework adapters."""

from __future__ import annotations

import asyncio
import functools
import inspect
from collections.abc import Callable, Sequence
from typing import Any, TypeVar

from agentic_sidecar.core.context import DecisionContext
from agentic_sidecar.core.sidecar import Sidecar

F = TypeVar("F", bound=Callable[..., Any])


def attach(sidecar: Sidecar, tools: Sequence[F]) -> list[F]:
    """Wrap each tool in `tools` so calling it first runs `sidecar.evaluate()`.

    Returns a new list in the same order -- pass it straight to
    `create_react_agent(model, tools=attach(sidecar, tools))`. Does not
    mutate the input list or the original tool callables.
    """
    return [_wrap_tool(sidecar, tool) for tool in tools]


def _wrap_tool(sidecar: Sidecar, tool: F) -> F:
    signature = inspect.signature(tool)
    tool_name = getattr(tool, "__name__", repr(tool))

    @functools.wraps(tool)
    def _sidecar_wrapped_tool(*args: Any, **kwargs: Any) -> Any:
        context = DecisionContext(
            tool_name=tool_name,
            tool_args=_bind_args(signature, args, kwargs),
        )
        decision = sidecar.evaluate(context)
        # Resolve governance before invoking the original function.
        decision = sidecar.enforce(context, decision)
        invocation = sidecar.runtime.dispatch(context, decision)
        try:
            result = tool(*args, **kwargs)
        except BaseException as exc:
            sidecar.runtime.complete(invocation, exc)
            raise
        sidecar.runtime.complete(invocation)
        return result

    if inspect.iscoroutinefunction(tool):

        @functools.wraps(tool)
        async def _async_wrapped_tool(*args: Any, **kwargs: Any) -> Any:
            context = DecisionContext(
                tool_name=tool_name,
                tool_args=_bind_args(signature, args, kwargs),
            )
            decision = await asyncio.to_thread(sidecar.evaluate, context)
            decision = await asyncio.to_thread(sidecar.enforce, context, decision)
            loop = asyncio.get_running_loop()
            owned_task: asyncio.Task[Any] | None = None
            invocation = ""

            def cancel_on_loop() -> None:
                if owned_task is not None and sidecar.runtime.is_running(invocation):
                    owned_task.cancel()

            def request_cancel() -> None:
                loop.call_soon_threadsafe(cancel_on_loop)

            invocation = sidecar.runtime.dispatch(context, decision, cancel=request_cancel)
            try:
                owned_task = asyncio.create_task(tool(*args, **kwargs))
                result = await owned_task
            except BaseException as exc:
                sidecar.runtime.complete(invocation, exc)
                raise
            sidecar.runtime.complete(invocation)
            return result

        return _async_wrapped_tool  # type: ignore[return-value]
    return _sidecar_wrapped_tool  # type: ignore[return-value]


def _bind_args(
    signature: inspect.Signature, args: tuple[Any, ...], kwargs: dict[str, Any]
) -> dict[str, Any]:
    try:
        bound = signature.bind(*args, **kwargs)
    except TypeError:
        # A call that doesn't match the tool's declared signature shouldn't
        # crash the Decision Gate -- fall back to raw kwargs (positional
        # args are lost in this case, but LangGraph's ToolNode always calls
        # tools with keyword arguments derived from the model's structured
        # tool call, so this path is a defensive fallback, not the norm).
        return dict(kwargs)
    bound.apply_defaults()
    arguments = dict(bound.arguments)
    for name, parameter in signature.parameters.items():
        if parameter.kind is inspect.Parameter.VAR_KEYWORD:
            arguments.update(arguments.pop(name, {}))
    return arguments
