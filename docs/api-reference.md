# API Reference

Python API for `agentic-sidecar` **0.8.1** (unchanged from 0.8.0). Imports below identify the supported
module for each symbol; intent and policy/risk types live in their subpackages.

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

Evaluate one proposed tool call. Injects intent/history into the caller's context,
computes a verdict, and stores a deep context copy in `sidecar.decisions`. Errors
from injection, dispatch, validation or recording resolve via `on_sidecar_failure`. This method does
not dispatch tools or raise merely because a verdict is BLOCK. See
[Failure handling](architecture.md#failure-configuration) for scope.

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

Decorator. Register an approval hook invoked by `enforce()` or the Govern
adapter for PAUSE/ESCALATE. Responses must match the decision ID and use an
ApprovalAction. See [Governance](governance.md) for resolution semantics.

```python
@sidecar.on_escalation_required
def handle_escalation(request: EscalationRequest) -> ApprovalResponse:
    ...
```

### `sidecar.decisions: list[tuple[DecisionContext, Decision]]`

In-memory log of evaluated context/decision pairs. Contexts and nested data
are deep-copied when recorded but remain mutable; caller-created `AuditRecord` objects are a separate export API.

### `sidecar.mode: str`

Current mode — `"observe"` or `"govern"`.

---

## `Decision`

```python
from agentic_sidecar import Decision, DecisionStatus, RiskLevel
```

Frozen Pydantic result of a Decision Gate evaluation; nested dictionary values
are not deeply immutable.

| Field | Type | Description |
|---|---|---|
| `decision_id` | `str` | Generated UUID; approval correlation ID |
| `status` | `DecisionStatus` | ALLOW / WARN / BLOCK / CHALLENGE / REPLAN / PAUSE / ESCALATE |
| `risk` | `RiskLevel` \| `None` | LOW / MEDIUM / HIGH; None when no classification was produced, including early policy returns and failure fallback |
| `reason` | `str` | Human-readable verdict explanation |
| `decision_point` | `str` \| `None` | Boundary name, commonly `"tool_call"` for built-in verdicts; optional for hooks/fallback |
| `trigger_details` | `dict` \| `None` | Optional tool name and argument snapshot |
| `escalation_required` | `bool` | Explicit escalation marker (default False); built-in budget/Judge PAUSE sets it |
| `causal_link` | `str` \| `None` | Optional caller-supplied causal identifier |

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
| `metadata` | `dict[str, Any]` | Caller metadata forwarded to evaluators |
| `boundary` | `"tool_call"` / `"plan"` | Evaluation boundary |
| `goal` | `str` | Goal when no active envelope exists |
| `plan` | `list[dict]` | Explicit plan steps |

---

## `SidecarBlockedError`

```python
from agentic_sidecar import SidecarBlockedError
```

Raised by the LangGraph callable wrapper in Govern mode when `decision.status == "BLOCK"`.

```python
try:
    (my_tool_wrapped,) = attach(sidecar, [my_tool])
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

Build a snapshot of application-supplied records and reporting state. This
does not fetch data from a running agent. `steps_completed` counts recorded calls.

### `StatusNarrator.get_narrative() -> str`

Return the full execution narrative as a human-readable string.

### `StatusNarrator.pause(reason: str) -> None` / `resume() -> None`

Record narrator pause/resume state; application code owns actual execution.

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

## Evaluators

```python
from agentic_sidecar import PlanEvaluator, CriticEvaluator, JudgeEvaluator
from agentic_sidecar.evaluators import EvaluatorResult, JudgeProvider
```

### `PlanEvaluator.evaluate(context: dict) -> EvaluatorResult`

Accepts plan dictionaries/PlanStep objects, goal, intent, constraints and
constraint_bindings. Selected tool/goal patterns and opposing tool pairs yield
REPLAN. Supplied bindings check plan arguments deterministically. min_confidence
filters the fixed 0.9 intervention score. No automatic natural-language bindings.

### `CriticEvaluator.evaluate(context: dict) -> EvaluatorResult`

Selected risky tool patterns, assumptions and permitted-action contradictions
yield CHALLENGE. Metadata authorized/eligibility_verified/backup_verified flags
can satisfy corresponding tool-call checks. threshold filters the fixed 0.85
score. These assertions are caller-supplied; full-plan checks are conservative.

### `JudgeEvaluator(provider, enabled=True, cost_limit=0.50, timeout_ms=5000, budget=None)`

Sync/async return validated EvaluatorResult with usage, provider, confidence and
latency. Errors propagate to Sidecar's failure policy. Returned usage is charged
once, including valid usage attached to an invalid verdict. cost_limit is a
post-response ceiling; exceeding it returns PAUSE. get_cost/reset_cost manage
tracked cost. See [Limitations](limitations.md) for late sync responses and async
cancellation. Choose MockJudge for offline examples; live OpenAIJudge and
AnthropicJudge require an explicit model, optional SDK and credentials.

### `JudgeProvider`

Implement evaluate(question, context) returning decision, reasoning, confidence
and usage with cost and total_tokens. Supported decisions are all seven statuses;
confidence must be finite in [0, 1], cost finite/nonnegative and tokens a
nonnegative integer. Override validate/evaluate_async as appropriate.
Without known cost, only cost_limit=None with no task budget is supported.

### `Sidecar.evaluate_plan(plan, *, goal="", metadata=None) -> Decision`

Requires a nonempty list of dictionaries with tool_name and optional arguments.
Checks policy/risk/intent per step, then enabled evaluators with full context.
Computes a verdict without executing steps. An active intent supplies the goal.

### `Sidecar.enforce(context, decision) -> Decision`

Adapter dispatch boundary: Observe returns unchanged; Govern resolves
PAUSE/ESCALATE and only returns ALLOW/WARN. BLOCK raises SidecarBlockedError;
other unresolved statuses raise SidecarSuspendedError. Both expose decision and
context. Applications must call enforce before dispatch in custom loops.

### `CLIApprovalHandler`

Import from agentic_sidecar.cli.approval and pass as escalation_handler.
Provides a local prompt for approve-once/reject/modify-intent/replan/stop.
The `approval-demo` CLI command tries the prompt without executing tools.

## Provenance exports

```python
from agentic_sidecar import AuditRecord, CausalLink, DecisionRationale, DecisionTrigger
```

Construct a caller-managed `AuditRecord` with decision ID, timestamp, outcome,
trigger, rationale, and optional causal/execution context. `to_dict()` serializes
the record, including ISO timestamp and structured causal links. TaskRuntime
automatically generates immutable event snapshots; EventJournal supplies
optional durable JSONL persistence. See [Live operations](live-operations.md).

## Top-level `__version__`

```python
from agentic_sidecar import __version__
print(__version__)  # "0.8.1"
```

## Runtime operations

Public exports: `TaskRuntime`, `RuntimeEvent`, `EventJournal`, `OperatorServer`.
Supply `runtime=TaskRuntime(...)` to Sidecar and `escalation_handler=runtime`
for remote approvals. Inspect `sidecar.runtime.snapshot()` and
`sidecar.runtime.journal.export(after=0)`. DecisionContext accepts
`parent_decision_id` and `parent_plan_step` for supplied plan causality.
See [Live operations](live-operations.md) for the full lifecycle and HTTP surface.

## Scoped supervision and native export (0.8)

Public exports: `ScopedSystem`, `ScopeLayer`, `ContextSpec`, `GuardrailSpec`,
`BoundAgent`. `ScopedSystem.bind(agent_id, on_sidecar_failure=..., mode=...)`
returns a separate Sidecar and explicit `context()` / `deliver(receiver)` payload.
See [scoped supervision](scoped-supervision.md) for configuration and limits.
`Sidecar` also accepts trusted `mandatory_checks`, `mandatory_configuration` and
`context_metadata`; checks run before custom hooks and the configuration is
included in audit policy fingerprints.

`integrations.correlation.Correlation` and `export_decisions()` provide native
versioned projections. See [integration contracts](integrations.md).
