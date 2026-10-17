# Integrations

## Framework adapters

All adapters share the same sync/async governed callable boundary. Supply plain,
typed Python functions with docstrings to `attach(sidecar, tools)` and pass the
returned tools to your framework. The core imports no framework SDK.

| Module / install extra | Returned surface | Tested SDK | Python |
| --- | --- | --- | --- |
| `adapters.langgraph` / `langgraph` | Typed callables for LangChain StructuredTool / LangGraph | LangGraph 1.x, LangChain Core 1.x | 3.10+ |
| `adapters.autogen` / `autogen` | AutoGen Core FunctionTool | 0.7.5 | 3.10+ |
| `adapters.crewai` / `crewai` | CrewAI Tool | 1.6.1 | 3.10–3.13 |
| `adapters.openai_agents` / `openai-agents` | OpenAI Agents FunctionTool | 0.24.0 | 3.10+ |
| `adapters.google_adk` / `google-adk` | ADK FunctionTool | 2.12.0 | 3.11+ |

The native SDK conformance job runs on Python 3.12; the core/LangGraph matrix
runs on 3.10–3.13. Other SDK/Python combinations are not independently certified.
SDK extras are pinned to the validated versions. CrewAI and ADK dependencies use
Python markers; an ineligible Python environment will not install that SDK.

```python
from agentic_sidecar import Sidecar
from agentic_sidecar.adapters.autogen import attach

sidecar = Sidecar(on_sidecar_failure="fail_closed", mode="govern")

def read_order(order_id: str) -> str:
    """Read an order."""
    return f"Order {order_id}"

# Install agentic-sidecar[autogen] before running this conversion.
tools = attach(sidecar, [read_order])
```

Observe records all seven verdicts and calls through. Govern executes ALLOW/WARN,
blocks BLOCK, and resolves or suspends PAUSE/ESCALATE/CHALLENGE/REPLAN. All adapters
use the same approval, explicit fail_open/fail_closed, stop and audit paths.
OpenAI tools disable SDK error conversion so governance exceptions propagate.
CrewAI `run()` also runs async callables; the shared async wrapper retains owned
cancellation. Frameworks may convert exceptions into model-visible errors; such
conversion never authorizes the denied tool invocation.

Supported inputs are plain typed callables, not prebuilt SDK tools, injected SDK
context parameters, hosted tools, automatic handoffs or agent-as-tool recursion.
Protect every nested boundary explicitly. Original functions and raw sessions
remain accessible to a trusted host: wrappers are not a sandbox. Use
[scoped supervision](scoped-supervision.md) for shared/exclusive composition.

## MCP

`agentic_sidecar.adapters.mcp.attach(sidecar, session, tool_names)` creates async
callables for allowlisted tools on an initialized MCP 2.3.0 `ClientSession`.
The MCP SDK owns transport/discovery. Client-side checks alone cannot contain an
agent holding the raw session. The gateway example also gates the server's tool,
keeps credentials server-side, rejects raw tool names and records actual execution.
See [examples](examples.md); production requires a separately secured service identity.

## Versioned native decision evidence

`sidecar.correlation/1` associates each decision with explicit run/trace/span IDs,
logical task/system/agent identity, source journal event, timestamp, policy hash,
boundary, tool name and the original seven-state decision (including causal ID).
The host must supply IDs for the exact session/span; exporting a mixed-span
Sidecar under one span is not automatic correlation.

```python
from agentic_sidecar import DecisionContext, Sidecar
from agentic_sidecar.integrations.correlation import Correlation, export_decisions

sidecar = Sidecar(on_sidecar_failure="fail_closed")
sidecar.evaluate(DecisionContext(tool_name="read"))
records = export_decisions(sidecar, Correlation(
    run_id="run-1", trace_id="trace-1", span_id="span-1",
))
```

Export verifies the complete native journal hash chain first. Projections omit the full DecisionContext; the original Decision trigger details
can contain tool arguments, and reasons can contain sensitive values. Authorize
readers and redact appropriately before exporting beyond that boundary.
A projection is not independently verifiable execution evidence. Hash chains detect
alteration/reordering, not a full rewrite by a malicious producer without an
external trusted anchor. AIOS mapping is a non-normative draft; stable schemas
remain v1.0 work.

## AgenticLens

Lens **0.7.1** provides `agenticlens.integrations.sidecar.attach_decisions(run, records)`
and native journal verification. Sidecar's optional helper
`agentic_sidecar.integrations.agenticlens.attach_decisions(sidecar, run, span_id=...)`
verifies the journal through Lens and exports the matching projection. Install the
`agenticlens` extra. Lens checks exact run/trace/span identity and atomically rejects
invalid/conflicting batches; duplicate records are idempotent. Diagnosis schema 1.1
adds supervision decisions to the timeline. BLOCK does not mark a span/run/deployment
failed; actual dispatch/completion remains native journal evidence.

## Agentic Chaos and Evals

`integrations.agentic_chaos.evaluate_recovery(sidecar, event, tool_name=..., arguments=...)`
checks/enforces a recovery proposal with a native Chaos event ID. It does not execute
it; actual dispatch still uses a supervised adapter. Tested against Chaos 0.5.3 and
0.6.0; the optional `agentic-chaos` extra admits `>=0.5.3,<0.7` since Sidecar 0.8.1.
Chaos 0.6.0 event IDs and shape are unchanged; its contracts and pytest plugin stay in Chaos.
Gate failure tests cover explicit fail_open/fail_closed; Chaos retains fault injection.
Evals 0.7.1 retains scoring/report ownership; comparative supervision evidence and
delegated authority remain v0.9 work. No core sibling dependency is introduced.

## Tower, AIOS and Semantica

Tower 0.5.2's existing native decision/journal reader retains producer outcomes and
separate deployment health. MCP 0.3.5's discovery boundary remains separate from a
live runtime. Compatibility checks do not imply remote operator bridging.
AIOS records the correlation convention as a draft, not stable conformance.
`integrations.semantica` and the empty `semantica` extra are reserved; no provenance
export or upstream compatibility is claimed until its API is validated.
