# Integrations

Agentic Sidecar attaches to your agent framework via adapter modules in `agentic_sidecar.adapters`. The core runtime has zero dependencies on any specific framework — adapters handle the interception boundary.

---

## LangGraph

**Status: Available — callable wrapping and Govern BLOCK**
**Install:** `pip install "agentic-sidecar[langgraph]"`

The `langgraph` adapter is the primary supported integration. It wraps a list of tool callables before passing them to `create_react_agent`.

### How it works

`attach(sidecar, tools)` wraps each tool so that calling it first runs `sidecar.evaluate()`. If `mode="govern"` and the decision is `BLOCK`, it raises `SidecarBlockedError` instead of calling the real tool.

```python
from agentic_sidecar import Sidecar, SidecarBlockedError
from agentic_sidecar.adapters.langgraph import attach
from agentic_sidecar.gate.policy import PolicyAdvisor, PolicyRule
from langgraph.prebuilt import create_react_agent

sidecar = Sidecar(
    on_sidecar_failure="fail_closed",
    mode="govern",
    policy=PolicyAdvisor([
        PolicyRule(tool="delete_*", effect="deny"),
    ]),
)

def read_order(order_id: str) -> dict:
    return {"order_id": order_id, "amount": 450.0}

def delete_customer(customer_id: str) -> dict:
    return {"status": "deleted"}

# Wrap tools — pass result directly to create_react_agent
tools = attach(sidecar, [read_order, delete_customer])
# Supply your configured chat model; scripted examples include an offline model.
agent = create_react_agent(model, tools=tools)

try:
    result = agent.invoke({"messages": [("user", "Delete customer cust_1001")]})
except SidecarBlockedError as exc:
    print(f"Blocked: {exc.decision.reason}")
```

### Observe vs Govern with LangGraph

In **Observe mode**: the wrapped tool always calls through regardless of the verdict. Use `sidecar.decisions` to review after the run.

In **Govern mode**: ALLOW/WARN execute; BLOCK raises SidecarBlockedError;
PAUSE/ESCALATE invoke approvals or suspend; CHALLENGE/REPLAN suspend. Catch
SidecarSuspendedError to return control to the agent loop. Plain async functions
are supported. See [Governance](governance.md) for approval configuration.

### Notes

- The adapter doesn't require `@tool` decorators — it works with plain Python callables
- It uses `inspect.signature` to bind call arguments into `DecisionContext.tool_args`
- Positional args are bound to parameter names; defaults are applied
- The examples use `create_react_agent` within the supported LangGraph major version; it emits a deprecation notice
- Additional frameworks and optional ecosystem bridges target 0.8

---

## CrewAI

**Status: Planned for 0.8**

The `adapters/crewai.py` module exists as a placeholder stub (no `attach()` function) and is not functional in v0.6.1. See [Roadmap](roadmap.md).

---

## AutoGen

**Status: Planned for 0.8**

The `adapters/autogen.py` module exists as a placeholder stub and is not functional in v0.6.1. See [Roadmap](roadmap.md).

---

## OpenAI Agents SDK

**Status: Planned for 0.8**

The `adapters/openai_agents.py` module exists as a placeholder stub and is not functional in v0.6.1. See [Roadmap](roadmap.md).

---

## Google ADK

**Status: Planned for 0.8**

The `adapters/google_adk.py` module exists as a placeholder stub and is not functional in v0.6.1. See [Roadmap](roadmap.md).

---

## Custom / generic Python agent

For any agent that doesn't use a specific framework, call `sidecar.evaluate()` directly:

```python
from agentic_sidecar import Sidecar, DecisionContext, SidecarBlockedError

sidecar = Sidecar(on_sidecar_failure="fail_closed", mode="govern")

def my_tool(param: str) -> str:
    context = DecisionContext(tool_name="my_tool", tool_args={"param": param})
    decision = sidecar.evaluate(context)

    if sidecar.mode == "govern" and decision.status == "BLOCK":
        raise SidecarBlockedError(decision, context)

    return f"processed {param}"
```

---

## AgenticLens integration

**Status: Planned for 0.8**

An optional bridge to [AgenticLens](https://deepagentlabs.io/agenticlens/) for unified tracing is declared in the package:

The reserved module is `agentic_sidecar.integrations.agenticlens`.

Install with: `pip install "agentic-sidecar[agenticlens]"`

This module is a placeholder. Actual trace forwarding from Sidecar to AgenticLens spans is a planned capability — see [Roadmap](roadmap.md).

---

## Agentic Chaos integration

**Status: Planned for 0.8**

The reserved module is `agentic_sidecar.integrations.agentic_chaos`.

Install with: `pip install "agentic-sidecar[agentic-chaos]"`

The extra reserves a dependency boundary; install it when a compatible
integration becomes available. See [Roadmap](roadmap.md).

## Ecosystem coordination

AgenticLens export, Chaos coordination, and Semantica provenance export target
0.8, with a shared correlation contract before cross-project export. Control
Tower consumes decision/status evidence while retaining deployment-health
semantics. Authority/delegation work targets 0.9; published AI Operations
Specification schemas target 1.0. See the [canonical plan](roadmap.md).
