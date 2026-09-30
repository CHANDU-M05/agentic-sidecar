# Getting Started

This page gets you from zero to a governed agent in under five minutes.

---

## Installation

Install the package from PyPI:

```bash
pip install agentic-sidecar
```

To use the LangGraph adapter (most common), install the optional extra:

```bash
pip install "agentic-sidecar[langgraph]"
```

**Requires Python ≥ 3.10.**

---

## Verify installation

```bash
python -c "import agentic_sidecar; print(agentic_sidecar.__version__)"
# 0.6.0

agentic-sidecar version
# agentic-sidecar 0.6.0
```

---

## Minimal example — Observe mode

The simplest integration wraps your tools and lets the Sidecar log decisions without blocking anything. This is the right starting point for an existing agent.

```python
from agentic_sidecar import Sidecar
from agentic_sidecar.adapters.langgraph import attach
from agentic_sidecar.gate.policy import PolicyAdvisor, PolicyRule
from agentic_sidecar.gate.risk import RiskEvaluator, RiskRule

# 1. Build the Sidecar
sidecar = Sidecar(
    on_sidecar_failure="fail_closed",   # required — no default
    mode="observe",                      # log decisions, never block
    policy=PolicyAdvisor([
        PolicyRule(tool="delete_*", effect="deny"),
    ]),
    risk=RiskEvaluator([
        RiskRule(tool="issue_refund", arg_name="amount", arg_op="gt", arg_value=500, risk="HIGH"),
    ]),
)

# 2. Wrap your tools
def read_order(order_id: str) -> dict:
    return {"order_id": order_id, "amount": 450.0}

def issue_refund(order_id: str, amount: float) -> dict:
    return {"status": "refunded", "amount": amount}

tools = attach(sidecar, [read_order, issue_refund])

# 3. Use with LangGraph
from langgraph.prebuilt import create_react_agent
agent = create_react_agent(model, tools=tools)
result = agent.invoke({"messages": [("user", "Refund order ORD-999 for $250")]})

# After the run, inspect decisions:
for ctx, decision in sidecar.decisions:
    print(f"{ctx.tool_name}: {decision.status} — {decision.reason}")
```

---

## Minimal example — Govern mode

Switch to `mode="govern"` to enforce decisions. A `BLOCK` verdict raises `SidecarBlockedError` and stops the tool call.

```python
from agentic_sidecar import Sidecar, SidecarBlockedError
from agentic_sidecar.adapters.langgraph import attach
from agentic_sidecar.gate.policy import PolicyAdvisor, PolicyRule

sidecar = Sidecar(
    on_sidecar_failure="fail_closed",
    mode="govern",
    policy=PolicyAdvisor([
        PolicyRule(tool="delete_*", effect="deny"),
    ]),
)

tools = attach(sidecar, [read_order, issue_refund, delete_customer])
agent = create_react_agent(model, tools=tools)

try:
    agent.invoke({"messages": [("user", "Delete customer record cust_1001")]})
except SidecarBlockedError as exc:
    print(f"Blocked: {exc.decision.reason}")
    print(f"Tool attempted: {exc.context.tool_name}")
```

---

## Next steps

- **[Architecture](architecture.md)** — understand the Decision Gate pipeline
- **[Features](features.md)** — see all evaluation modules and their status
- **[Configuration](configuration.md)** — full reference for all Sidecar options
- **[Examples](examples.md)** — runnable scripts for common scenarios
