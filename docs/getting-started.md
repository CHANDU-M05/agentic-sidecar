# Getting Started

Start with deterministic tool-call supervision using the **0.6.1** API.
This release is prepared in the checkout; install from source until its tagged
package is published.
These examples run without a model, framework installation, or API key.

## Installation

Requires Python 3.10 or newer. Until 0.6.1 is published to PyPI, install this
checkout so the API on this page matches what you have installed:

```bash
pip install -e .
agentic-sidecar version
```

Once 0.6.1 is published, install normally:

```bash
pip install agentic-sidecar
agentic-sidecar version
```

For the repository examples:

```bash
uv sync --extra dev --extra langgraph
uv run agentic-sidecar version
```

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
