# Getting Started

Start with deterministic tool-call supervision using the **0.8.1** API (unchanged from 0.8.0).
These examples run without a model, framework installation, or API key.

## Installation

Requires Python 3.10 or newer. Install the v0.8.1 package from PyPI:

```bash
pip install agentic-sidecar==0.8.1
# Optional live Judge SDKs:
pip install "agentic-sidecar[openai,anthropic]==0.8.1"
```

For development from a checkout, run `uv sync --extra dev --extra langgraph --extra docs`.

## Observe a proposed action

```python
from agentic_sidecar import DecisionContext, Sidecar
from agentic_sidecar.gate.policy import PolicyAdvisor, PolicyRule

sidecar = Sidecar(
    on_sidecar_failure="fail_closed",
    policy=PolicyAdvisor([PolicyRule(tool="delete_*", effect="deny")]),
)
decision = sidecar.evaluate(DecisionContext(tool_name="delete_customer"))
print(decision.status)  # BLOCK
```

`evaluate()` computes and records the verdict. Execution is handled by the
caller or an adapter. Observe mode lets wrapped tools run regardless of verdict.

## Enforce an intent constraint

```python
from agentic_sidecar import Sidecar, SidecarBlockedError
from agentic_sidecar.adapters.langgraph import attach
from agentic_sidecar.intent import ConstraintBinding, IntentEnvelope, IntentGuardian, Requester

def issue_refund(order_id: str, amount: float) -> str:
    """Issue a refund for an order."""
    return f"refunded {amount} for {order_id}"

envelope = IntentEnvelope(
    goal="Refund order A100 up to $500",
    requested_by=Requester(id="support_lead"),
    constraints={"maximum_refund": 500},
)
guardian = IntentGuardian(envelope, [ConstraintBinding(
    constraint="maximum_refund", tool="issue_refund", arg_name="amount", op="lte",
)])
sidecar = Sidecar(
    on_sidecar_failure="fail_closed", mode="govern",
    intent=guardian, roles=["policy", "risk", "intent_guardian"],
)
(refund,) = attach(sidecar, [issue_refund])
print(refund("A100", 120))  # refunded 120 for A100
try:
    refund("A100", 850)
except SidecarBlockedError as exc:
    print(exc.decision.status)  # BLOCK; refund function was not called
```

The wrapper works with plain callables. To build an actual LangGraph agent,
install `agentic-sidecar[langgraph]` and run the scripted graph examples in
[Examples](examples.md). They include a model fixture and graph invocation.

Govern permits ALLOW/WARN, stops BLOCK, resolves PAUSE/ESCALATE through a
registered handler, and suspends unresolved outcomes plus CHALLENGE/REPLAN.
See [Governance](governance.md) and [supported scope](limitations.md).

## Next steps

- [Configuration](configuration.md): roles, policy/risk rules, intent, budget.
- [Features](features.md): evaluator and narration usage.
- [Architecture](architecture.md): boundary responsibilities and decision flow.
- [CLI reference](cli-reference.md): local status and simulated demo commands.
- [Roadmap](roadmap.md): live status in 0.7 and additional adapters in 0.8.
