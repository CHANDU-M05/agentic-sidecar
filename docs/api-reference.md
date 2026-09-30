# API Reference

Full Python API for `agentic-sidecar` v0.6.0. All public symbols are importable from the top-level package.

```python
import agentic_sidecar
```

---

## `Sidecar`

```python
from agentic_sidecar import Sidecar
```

The central class. Owns the Decision Gate and all evaluation module configuration.

### `__init__`

See [Configuration](configuration.md) for the full parameter reference.

### `evaluate(context: DecisionContext) -> Decision`

Evaluate one proposed tool call. Injects active intent and decision history into `context` before evaluation. Always returns a `Decision` — never raises (errors resolve via `on_sidecar_failure`). Records the result in `sidecar.decisions`.

```python
from agentic_sidecar import DecisionContext

context = DecisionContext(tool_name="issue_refund", tool_args={"amount": 250.0})
decision = sidecar.evaluate(context)
print(decision.status)  # "ALLOW"
```

### `set_intent(intent: IntentGuardian | None) -> None`

Set or clear the active `IntentGuardian`. Raises `ValueError` if `intent` is provided but `"intent_guardian"` is not in `sidecar.roles`.

### `before_tool_call(func: Callable) -> Callable`

Decorator. Register a custom decision hook that replaces the entire built-in Decision Gate pipeline.

```python
@sidecar.before_tool_call
def my_hook(context: DecisionContext) -> Decision:
    ...
```

### `on_escalation_required(func: Callable) -> Callable`

Decorator. Register a custom escalation handler for PAUSE/ESCALATE decisions.

```python
@sidecar.on_escalation_required
def handle_escalation(request: EscalationRequest) -> ApprovalResponse:
    ...
```

### `sidecar.decisions: list[tuple[DecisionContext, Decision]]`

Audit trail of every (context, decision) pair evaluated since construction.

### `sidecar.mode: str`

Current mode — `"observe"` or `"govern"`.

---

## `Decision`

```python
from agentic_sidecar import Decision, DecisionStatus, RiskLevel
```

Immutable result of one Decision Gate evaluation.

| Field | Type | Description |
|---|---|---|
| `status` | `DecisionStatus` | ALLOW / WARN / BLOCK / CHALLENGE / REPLAN / PAUSE / ESCALATE |
| `risk` | `RiskLevel` \| `None` | LOW / MEDIUM / HIGH, or None if Risk Evaluator not enabled |
| `reason` | `str` | Human-readable verdict explanation |
| `decision_point` | `str` | Always `"tool_call"` in v0.6 |
| `trigger_details` | `dict` | `{"tool_name": ..., "arguments": ...}` |
| `escalation_required` | `bool` | True for PAUSE/ESCALATE decisions |

---

## `DecisionContext`

```python
from agentic_sidecar import DecisionContext
```

The input to `sidecar.evaluate()`. Build one per tool call.

| Field | Type | Description |
|---|---|---|
| `tool_name` | `str` | Name of the proposed tool |
| `tool_args` | `dict[str, Any]` | Arguments for the tool call |
| `intent` | `IntentSnapshot` \| `None` | Injected by `evaluate()` — do not set manually |
| `history` | `list[HistoryEntry]` | Injected by `evaluate()` — do not set manually |

---

## `SidecarBlockedError`

```python
from agentic_sidecar import SidecarBlockedError
```

Raised by the LangGraph adapter (and other adapters) in Govern mode when `decision.status == "BLOCK"`.

```python
try:
    tools = attach(sidecar, [my_tool])
    my_tool_wrapped()
except SidecarBlockedError as exc:
    print(exc.decision.reason)
    print(exc.context.tool_name)
```

| Attribute | Type | Description |
|---|---|---|
| `decision` | `Decision` | The blocking decision |
| `context` | `DecisionContext` | The context that triggered the block |

---

## `PolicyAdvisor`

```python
from agentic_sidecar.gate.policy import PolicyAdvisor, PolicyRule, PolicyResult
```

See [Configuration — PolicyAdvisor](configuration.md#policyadvisor-configuration) for full details.

### `PolicyAdvisor.evaluate(context: DecisionContext) -> PolicyResult`

Runs the rule set. Returns the first matching rule's result, or the default.

### `PolicyAdvisor.from_yaml(path) -> PolicyAdvisor` · `PolicyAdvisor.from_mapping(data) -> PolicyAdvisor`

Class methods to load rules from a YAML file or parsed dict.

---

## `RiskEvaluator`

```python
from agentic_sidecar.gate.risk import RiskEvaluator, RiskRule, RiskResult
```

### `RiskEvaluator.evaluate(context: DecisionContext) -> RiskResult`

Runs the rule set. Returns the first matching rule's risk classification, or the default.

---

## `BudgetGuardian`

```python
from agentic_sidecar.gate import BudgetGuardian, BudgetResult
```

### `BudgetGuardian.record_invocation(cost: float, tokens: int | None = None) -> None`

Accumulate cost and token usage.

### `BudgetGuardian.evaluate() -> BudgetResult`

Check current totals against ceilings. Returns `BudgetResult(exceeded, remaining_cost, remaining_tokens, reason)`.

### `BudgetGuardian.is_at_capacity() -> bool`

Quick check — returns `True` if already at or over budget.

### `BudgetGuardian.reset() -> None`

Reset cost and token counters to zero (for a new task).

---

## `IntentGuardian` / `IntentEnvelope` / `ConstraintBinding`

```python
from agentic_sidecar.intent import (
    IntentEnvelope, IntentGuardian, ConstraintBinding, Requester
)
```

See [Configuration — IntentEnvelope and IntentGuardian](configuration.md#intentenvelope-and-intentguardian-configuration).

### `IntentEnvelope.is_expired(now=None) -> bool`

Returns `True` if `expires` is set and the envelope has expired.

### `IntentEnvelope.to_snapshot() -> IntentSnapshot`

Returns a lightweight `IntentSnapshot(goal, constraints)` — the form injected into `DecisionContext`.

---

## `EscalationHandler` / `EscalationRequest` / `ApprovalResponse` / `ApprovalAction`

```python
from agentic_sidecar.gate import (
    EscalationHandler, EscalationRequest, ApprovalResponse, ApprovalAction
)
```

**`ApprovalAction` values:** `APPROVE_ONCE`, `REJECT`, `MODIFY_INTENT`, `ASK_AGENT_TO_REPLAN`, `STOP_AGENT`

---

## `StatusNarrator` / `StatusNarrative` / `ToolCallNarrative`

```python
from agentic_sidecar.status import StatusNarrator, StatusNarrative, ToolCallNarrative
```

### `StatusNarrator.set_objective(objective: str) -> None`

Record the top-level task objective.

### `StatusNarrator.record_tool_call(tool_name, arguments, decision=None, risk_level=None, intent_compliant=True) -> ToolCallNarrative`

Record a tool invocation and generate its narrative.

### `StatusNarrator.get_status(...) -> StatusNarrative`

Build a complete live status snapshot with all tracked metrics.

### `StatusNarrator.get_narrative() -> str`

Return the full execution narrative as a human-readable string.

### `StatusNarrator.pause(reason: str) -> None` / `resume() -> None`

Record pause and resume state.

---

## `attach` (LangGraph adapter)

```python
from agentic_sidecar.adapters.langgraph import attach
```

### `attach(sidecar: Sidecar, tools: Sequence[F]) -> list[F]`

Wraps each tool in `tools` so calling it first runs `sidecar.evaluate()`. Returns a new list in the same order. Does not mutate the input list or original tool callables.

```python
tools = attach(sidecar, [read_order, issue_refund, delete_customer])
agent = create_react_agent(model, tools=tools)
```

---

## Top-level `__version__`

```python
from agentic_sidecar import __version__
print(__version__)  # "0.6.0"
```
