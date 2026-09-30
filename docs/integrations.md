# Integrations

Agentic Sidecar attaches to your agent framework via adapter modules in `agentic_sidecar.adapters`. The core runtime has zero dependencies on any specific framework — adapters handle the interception boundary.

---

## LangGraph

**Status: Stable**  
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
agent = create_react_agent(model, tools=tools)

try:
    result = agent.invoke({"messages": [("user", "Delete customer cust_1001")]})
except SidecarBlockedError as exc:
    print(f"Blocked: {exc.decision.reason}")
```

### Observe vs Govern with LangGraph

In **Observe mode**: the wrapped tool always calls through regardless of the verdict. Use `sidecar.decisions` to review after the run.

In **Govern mode**: `BLOCK` raises `SidecarBlockedError`. `ALLOW` and `WARN` both pass through.

### Notes

- The adapter doesn't require `@tool` decorators — it works with plain Python callables
- It uses `inspect.signature` to bind call arguments into `DecisionContext.tool_args`
- Positional args are bound to parameter names; keyword args are passed as-is

---

## CrewAI

**Status: Planned — not yet implemented**

The `adapters/crewai.py` module exists as a placeholder stub (no `attach()` function) and is not functional in v0.6.0. See [Roadmap](roadmap.md).

---

## AutoGen

**Status: Planned — not yet implemented**

The `adapters/autogen.py` module exists as a placeholder stub and is not functional in v0.6.0. See [Roadmap](roadmap.md).

---

## OpenAI Agents SDK

**Status: Planned — not yet implemented**

The `adapters/openai_agents.py` module exists as a placeholder stub and is not functional in v0.6.0. See [Roadmap](roadmap.md).

---

## Google ADK

**Status: Planned — not yet implemented**

The `adapters/google_adk.py` module exists as a placeholder stub and is not functional in v0.6.0. See [Roadmap](roadmap.md).

---

## Custom / generic Python agent

For any agent that doesn't use a specific framework, call `sidecar.evaluate()` directly:

```python
from agentic_sidecar import Sidecar, DecisionContext, SidecarBlockedError

sidecar = Sidecar(on_sidecar_failure="fail_closed", mode="govern", ...)

def my_tool(param: str) -> str:
    context = DecisionContext(tool_name="my_tool", tool_args={"param": param})
    decision = sidecar.evaluate(context)

    if sidecar.mode == "govern" and decision.status == "BLOCK":
        raise SidecarBlockedError(decision, context)

    # ... actual tool logic
    return result
```

---

## AgenticLens integration

**Status: Placeholder — not yet implemented**

An optional bridge to [AgenticLens](https://deepagentlabs.io/agenticlens/) for unified tracing is declared in the package:

```python
from agentic_sidecar.integrations.agenticlens import ...  # placeholder
```

Install with: `pip install "agentic-sidecar[agenticlens]"`

This module is a placeholder. Actual trace forwarding from Sidecar to AgenticLens spans is a planned capability — see [Roadmap](roadmap.md).

---

## Agentic Chaos integration

**Status: Placeholder — not yet implemented**

```python
from agentic_sidecar.integrations.agentic_chaos import ...  # placeholder
```

Install with: `pip install "agentic-sidecar[agentic-chaos]"`

Also a placeholder. See [Roadmap](roadmap.md).
