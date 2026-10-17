"""LangGraph interception adapter -- the first and, until it's proven out,
only decision-boundary hook (ROADMAP.md's Design Constraint 1).

`attach()` wraps a list of tool callables -- the same list you'd otherwise
hand to `langgraph.prebuilt.create_react_agent(model, tools=...)` -- so that
every invocation is evaluated by a `Sidecar` first. This module has no
import-time dependency on the `langgraph` package itself: it only relies on
LangGraph/LangChain's convention that a tool is a plain callable with a
stable `__name__` and a type-annotated signature, which is exactly what
`create_react_agent` accepts without an explicit `@tool` decorator. Install
`agentic-sidecar[langgraph]` to actually build and run a graph around the
wrapped tools (see `examples/`).

Observe records verdicts and calls through. Govern calls Sidecar.enforce:
ALLOW/WARN proceed, BLOCK raises SidecarBlockedError, PAUSE/ESCALATE invoke
local approvals or suspend, and CHALLENGE/REPLAN raise SidecarSuspendedError.
Plain sync and async functions are supported; async evaluation/approval runs
in a worker thread before awaiting the original function.
"""

from agentic_sidecar.adapters.callable import _bind_args as _bind_args
from agentic_sidecar.adapters.callable import attach as attach
