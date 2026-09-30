# Features

All capabilities listed here are **implemented and verified** against the current source code (v0.6.0). Planned capabilities appear only in [Roadmap](roadmap.md).

---

## Policy Advisor

**Status: Stable**

Evaluates proposed tool calls against a YAML-driven allow/deny rule set. Rules are matched using `fnmatch` glob patterns against the tool name. Rules are evaluated in order; the first match wins.

**What it does:** Answers "is this tool call permitted?" with zero LLM calls.

**How to enable:**
```python
from agentic_sidecar.gate.policy import PolicyAdvisor, PolicyRule

policy = PolicyAdvisor([
    PolicyRule(tool="delete_*", effect="deny", reason="Destructive ops require human sign-off"),
    PolicyRule(tool="read_*", effect="allow"),
])
sidecar = Sidecar(on_sidecar_failure="fail_closed", policy=policy)
```

**YAML rule format (via `PolicyAdvisor.from_yaml()`):**
```yaml
default: allow
rules:
  - tool: "delete_*"
    effect: deny
    reason: "Destructive operations blocked"
  - tool: "read_*"
    effect: allow
```

**Inputs:** `tool_name` from `DecisionContext`  
**Outputs:** `PolicyResult(effect, reason, matched_rule)`  
**Limitations:** Glob matching only — no regex, no argument-based policy rules (those belong in Risk Evaluator).

---

## Risk Evaluator

**Status: Stable**

Classifies a proposed tool call into `LOW`, `MEDIUM`, or `HIGH` risk. Rules match on tool name (glob) and optionally on a specific argument value using comparison operators (`eq`, `lt`, `lte`, `gt`, `gte`, `ne`).

**What it does:** Answers "how risky is this action?" and blocks if risk ≥ threshold.

**How to enable:**
```python
from agentic_sidecar.gate.risk import RiskEvaluator, RiskRule

risk = RiskEvaluator([
    RiskRule(
        tool="issue_refund",
        arg_name="amount",
        arg_op="gt",
        arg_value=500,
        risk="HIGH",
        reason="Refund exceeds standard authorization limit",
    ),
    RiskRule(tool="delete_*", risk="HIGH"),
])
sidecar = Sidecar(
    on_sidecar_failure="fail_closed",
    risk=risk,
    risk_block_threshold="HIGH",   # default
)
```

**YAML rule format (via `RiskEvaluator.from_yaml()`):**
```yaml
default: LOW
rules:
  - tool: "issue_refund"
    arg_name: amount
    arg_op: gt
    arg_value: 500
    risk: HIGH
  - tool: "delete_*"
    risk: HIGH
```

**Inputs:** `tool_name`, `tool_args` from `DecisionContext`  
**Outputs:** `RiskResult(risk, reason, matched_rule)`  
**Limitations:** Static rules only — no semantic understanding of argument meaning. LLM-based risk scoring is a future capability (see Roadmap).

---

## Intent Guardian

**Status: Stable**

Validates tool arguments against structured `ConstraintBinding`s derived from a user-declared `IntentEnvelope`. Detects drift between what the user requested and what the agent is attempting.

**What it does:** Answers "does this action stay within what the user actually asked for?"

**How to enable:**
```python
from agentic_sidecar.intent import IntentEnvelope, IntentGuardian, ConstraintBinding, Requester

envelope = IntentEnvelope(
    goal="Assist customer dispute — refund up to $500",
    requested_by=Requester(type="human", id="user_12"),
    constraints={"maximum_refund": 500.0},
)

binding = ConstraintBinding(
    constraint="maximum_refund",
    tool="issue_refund",
    arg_name="amount",
    op="lte",
    severity="BLOCK",
)

guardian = IntentGuardian(envelope, [binding])
sidecar = Sidecar(
    on_sidecar_failure="fail_closed",
    intent=guardian,
    roles=["policy", "risk", "intent_guardian"],
)
```

**Inputs:** `tool_name`, `tool_args`, active `IntentEnvelope.constraints`  
**Outputs:** `AlignmentResult(status, reason, findings)`  
**Limitations:** Only `constraints` enforcement is implemented. `authority` field on the envelope is carried but not enforced yet. See [Roadmap](roadmap.md).

---

## Budget Guardian

**Status: Stable**

Tracks cumulative cost (USD) and token usage across a task's execution. When either ceiling is reached, returns a `PAUSE` decision requiring human approval before continuing.

**What it does:** Answers "have we spent too much?" and pauses before overspending.

**How to enable:**
```python
from agentic_sidecar.gate import BudgetGuardian

budget = BudgetGuardian(max_cost=5.00, max_tokens=10_000)
sidecar = Sidecar(
    on_sidecar_failure="fail_closed",
    budget=budget,
    roles=["policy", "risk", "budget"],
)

# Record usage after each LLM call:
budget.record_invocation(cost=0.03, tokens=1200)
```

**Inputs:** Accumulated `current_cost` and `current_tokens`  
**Outputs:** `BudgetResult(exceeded, remaining_cost, remaining_tokens, reason)`  
**Limitations:** Manual call to `record_invocation()` is required — automatic cost tracking from LangGraph's callback system is a planned capability.

---

## Plan Evaluator

**Status: Experimental**

Evaluates a proposed multi-step plan for unnecessary steps, overreach, or contradictory operations. Returns `REPLAN` if the plan needs revision, or `BLOCK` if it is unsafe.

**What it does:** Reviews the agent's execution plan before it runs, not just individual tool calls.

**How to enable:**
```python
from agentic_sidecar.evaluators import PlanEvaluator, PlanStep

planner = PlanEvaluator(enabled=True)
sidecar = Sidecar(
    on_sidecar_failure="fail_closed",
    planner=planner,
    roles=["policy", "risk", "planner"],
)
```

**Inputs:** `tool_name`, `tool_args`, `history`, `intent` from `DecisionContext`  
**Outputs:** `EvaluatorResult(status, rationale)` — status is `ALLOW`, `REPLAN`, or `BLOCK`  
**Limitations:** Rule-based only; LLM-assisted plan evaluation is planned. Not connected to a real planning graph yet.

---

## Critic Evaluator

**Status: Experimental**

Challenges decisions for unsupported assumptions. Returns a `CHALLENGE` decision when the proposed tool call appears to rely on unverified or overly broad assumptions.

**How to enable:**
```python
from agentic_sidecar.evaluators import CriticEvaluator

critic = CriticEvaluator(enabled=True)
sidecar = Sidecar(
    on_sidecar_failure="fail_closed",
    critic=critic,
    roles=["policy", "risk", "critic"],
)
```

**Inputs:** `tool_name`, `tool_args`, `history`, `intent`  
**Outputs:** `EvaluatorResult(status, rationale)` — status is `ALLOW` or `CHALLENGE`  
**Limitations:** Experimental. Rule-based heuristics; full LLM-backed critique is planned.

---

## Judge Evaluator

**Status: Experimental**

Provides model-agnostic LLM-based decision review. Supports OpenAI and Anthropic providers. Returns one of: `BLOCK`, `CHALLENGE`, `WARN`, `PAUSE`, or `ALLOW`.

**What it does:** A second-opinion LLM review of borderline decisions.

**How to enable:**
```python
from agentic_sidecar.evaluators import JudgeEvaluator, OpenAIJudge

judge = JudgeEvaluator(
    provider=OpenAIJudge(model="gpt-4o"),
    enabled=True,
)
sidecar = Sidecar(
    on_sidecar_failure="fail_closed",
    judge=judge,
    roles=["policy", "risk", "judge"],
)
```

**Inputs:** `tool_name`, `tool_args`, `history`, `intent`  
**Outputs:** `EvaluatorResult(status, rationale)`  
**Limitations:** Adds LLM latency and API cost per evaluated call. Only use when rule-based evaluation is insufficient.

---

## Status Narrator

**Status: Stable**

Translates raw tool calls and Decision Gate outcomes into human-readable narrative. Records objective, step progress, intent violations, risk, budget status, and pause state.

**How to use:**
```python
from agentic_sidecar.status import StatusNarrator

narrator = StatusNarrator()
narrator.set_objective("Resolve customer dispute for order ORD-999")

call = narrator.record_tool_call(
    tool_name="read_order",
    arguments={"order_id": "ORD-999"},
    decision=decision,
    risk_level="LOW",
)
print(call.narrative)      # "📥 Retrieving records"
print(narrator.get_narrative())
```

**Limitations:** Narration is heuristic-based on common tool name patterns. LLM-backed narration is planned.

---

## Human Escalation

**Status: Stable (data structures); Experimental (handler integration)**

Provides structured request/response types for pausing execution and collecting human approval on `PAUSE`/`ESCALATE` decisions.

```python
from agentic_sidecar.gate import EscalationHandler, ApprovalAction

@sidecar.on_escalation_required
def handle_approval(request):
    # Custom approval UI or CLI prompt
    return ApprovalResponse(
        decision_id=request.decision_id,
        action=ApprovalAction.APPROVE_ONCE,
    )
```

**Limitations:** The default `EscalationHandler.handle_escalation()` raises `NotImplementedError`. You must register a custom handler via `@sidecar.on_escalation_required`. CLI prompt integration is planned.

---

## Custom Decision Hook

**Status: Stable**

Override the entire Decision Gate with a custom callable using the `@sidecar.before_tool_call` decorator.

```python
@sidecar.before_tool_call
def my_evaluator(context: DecisionContext) -> Decision:
    if context.tool_name == "drop_table":
        return Decision(status="BLOCK", risk="HIGH", reason="Never")
    return Decision(status="ALLOW", risk="LOW", reason="OK")
```

**Limitations:** The custom hook fully replaces all built-in modules — there is no mechanism to run both a hook and the built-in pipeline simultaneously.
