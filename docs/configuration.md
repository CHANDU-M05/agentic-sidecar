# Configuration

This page covers all configuration options for the `Sidecar` constructor and its module dependencies.

---

## `Sidecar` constructor

```python
from agentic_sidecar import Sidecar

sidecar = Sidecar(
    on_sidecar_failure: Literal["fail_open", "fail_closed"],  # REQUIRED — no default
    policy: PolicyAdvisor | None = None,
    risk: RiskEvaluator | None = None,
    intent: IntentGuardian | None = None,
    budget: BudgetGuardian | None = None,
    planner: PlanEvaluator | None = None,
    critic: CriticEvaluator | None = None,
    judge: JudgeEvaluator | None = None,
    escalation_handler: EscalationHandler | None = None,
    risk_block_threshold: RiskLevel = "HIGH",
    mode: Literal["observe", "govern"] = "observe",
    roles: Sequence[str] | None = None,
)
```

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `on_sidecar_failure` | `"fail_open"` \| `"fail_closed"` | **Required** | What to do if evaluation itself raises. `"fail_closed"` → `BLOCK`; `"fail_open"` → `ALLOW`. |
| `policy` | `PolicyAdvisor` \| `None` | `PolicyAdvisor()` (empty) | Allow/deny rule set. An empty advisor allows everything. |
| `risk` | `RiskEvaluator` \| `None` | `RiskEvaluator()` (empty) | Risk classification rules. An empty evaluator classifies everything as `LOW`. |
| `intent` | `IntentGuardian` \| `None` | `None` | Active intent guardian. Only consulted if `"intent_guardian"` is in `roles`. |
| `budget` | `BudgetGuardian` \| `None` | `None` | Budget ceiling tracker. Only consulted if `"budget"` is in `roles`. |
| `planner` | `PlanEvaluator` \| `None` | `None` | Plan evaluator. Only consulted if `"planner"` is in `roles`. |
| `critic` | `CriticEvaluator` \| `None` | `None` | Critic evaluator. Only consulted if `"critic"` is in `roles`. |
| `judge` | `JudgeEvaluator` \| `None` | `None` | LLM judge evaluator. Only consulted if `"judge"` is in `roles`. |
| `escalation_handler` | `EscalationHandler` \| `None` | `None` | Handler for PAUSE/ESCALATE decisions. |
| `risk_block_threshold` | `"LOW"` \| `"MEDIUM"` \| `"HIGH"` | `"HIGH"` | Minimum risk level that triggers a `BLOCK`. |
| `mode` | `"observe"` \| `"govern"` | `"observe"` | Observe logs decisions; Govern enforces them. |
| `roles` | `Sequence[str]` \| `None` | `["policy", "risk"]` | Which evaluation modules to run. |

---

## `roles` — controlling which modules run

The `roles` parameter is the main switch for enabling/disabling evaluation modules. Only modules listed in `roles` are consulted during `evaluate()`.

**Supported roles:**

| Role | Module |
|---|---|
| `"policy"` | Policy Advisor |
| `"risk"` | Risk Evaluator |
| `"intent_guardian"` | Intent Guardian |
| `"budget"` | Budget Guardian |
| `"planner"` | Plan Evaluator |
| `"critic"` | Critic Evaluator |
| `"judge"` | Judge Evaluator |

**Default roles when `roles=None`:** `["policy", "risk"]`

**Example — all non-LLM modules:**
```python
sidecar = Sidecar(
    on_sidecar_failure="fail_closed",
    mode="govern",
    policy=policy,
    risk=risk,
    intent=guardian,
    budget=budget,
    roles=["policy", "risk", "intent_guardian", "budget"],
)
```

---

## `PolicyAdvisor` configuration

```python
from agentic_sidecar.gate.policy import PolicyAdvisor, PolicyRule

# In-code rules
policy = PolicyAdvisor(
    rules=[PolicyRule(tool="delete_*", effect="deny")],
    default_effect="allow",   # default when no rule matches
)

# From YAML file
policy = PolicyAdvisor.from_yaml("policies/my_policy.yaml")

# From a dict (useful in tests)
policy = PolicyAdvisor.from_mapping({
    "default": "allow",
    "rules": [{"tool": "delete_*", "effect": "deny"}],
})
```

**`PolicyRule` fields:**

| Field | Type | Default | Description |
|---|---|---|---|
| `tool` | `str` | Required | `fnmatch` glob pattern matched against tool name |
| `effect` | `"allow"` \| `"deny"` | Required | Verdict when this rule matches |
| `reason` | `str` \| `None` | `None` | Human-readable explanation |

---

## `RiskEvaluator` configuration

```python
from agentic_sidecar.gate.risk import RiskEvaluator, RiskRule

risk = RiskEvaluator(
    rules=[
        RiskRule(tool="issue_refund", arg_name="amount", arg_op="gt", arg_value=500, risk="HIGH"),
        RiskRule(tool="delete_*", risk="HIGH"),
    ],
    default_risk="LOW",
)
```

**`RiskRule` fields:**

| Field | Type | Default | Description |
|---|---|---|---|
| `tool` | `str` | Required | `fnmatch` glob pattern |
| `risk` | `"LOW"` \| `"MEDIUM"` \| `"HIGH"` | Required | Risk level when this rule matches |
| `reason` | `str` \| `None` | `None` | Human-readable explanation |
| `arg_name` | `str` \| `None` | `None` | Argument to check (optional) |
| `arg_op` | `ArgOp` | `"eq"` | Comparison operator: `eq`, `lt`, `lte`, `gt`, `gte`, `ne` |
| `arg_value` | `Any` | `None` | Value to compare against |

---

## `BudgetGuardian` configuration

```python
from agentic_sidecar.gate import BudgetGuardian

budget = BudgetGuardian(
    max_cost=5.00,       # USD ceiling
    max_tokens=10_000,   # token ceiling (optional)
)

# Record usage manually after each LLM/tool invocation
budget.record_invocation(cost=0.03, tokens=1200)

# Reset for the next task
budget.reset()
```

---

## `IntentEnvelope` and `IntentGuardian` configuration

```python
from agentic_sidecar.intent import (
    IntentEnvelope, IntentGuardian, ConstraintBinding, Requester
)
from datetime import datetime, timezone

envelope = IntentEnvelope(
    goal="Assist customer dispute — refund up to $500",
    requested_by=Requester(type="human", id="user_42"),
    constraints={"maximum_refund": 500.0},
    authority={"can_delete": False},
    expires=datetime(2026, 12, 31, 23, 59, tzinfo=timezone.utc),  # optional
)

bindings = [
    ConstraintBinding(
        constraint="maximum_refund",
        tool="issue_refund",
        arg_name="amount",
        op="lte",
        severity="BLOCK",
    )
]

guardian = IntentGuardian(envelope, bindings)
```

**`ConstraintBinding` fields:**

| Field | Type | Default | Description |
|---|---|---|---|
| `constraint` | `str` | Required | Key in `envelope.constraints` |
| `tool` | `str` | Required | `fnmatch` glob for tool name |
| `arg_name` | `str` | Required | Argument to check |
| `op` | `ArgOp` | `"lte"` | Comparison operator |
| `severity` | `"WARN"` \| `"BLOCK"` | `"BLOCK"` | Decision outcome when violated |
| `reason` | `str` \| `None` | `None` | Override the auto-generated reason |

---

## Updating intent at runtime

A long-lived `Sidecar` is expected to serve one `IntentEnvelope` per task. Use `set_intent()` between tasks:

```python
# Before task 1
sidecar.set_intent(IntentGuardian(envelope_1, bindings_1))
agent.invoke(task_1)

# Before task 2
sidecar.set_intent(IntentGuardian(envelope_2, bindings_2))
agent.invoke(task_2)

# Clear intent
sidecar.set_intent(None)
```

> **Note:** `set_intent()` raises `ValueError` if you pass an `IntentGuardian` but `"intent_guardian"` is not in `sidecar.roles`.
