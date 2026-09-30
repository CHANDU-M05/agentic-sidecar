# Architecture

Agentic Sidecar is built on a single architectural principle: **the Main Agent acts; the Sidecar observes, thinks, advises, and governs.**

---

## Core design

```
┌─────────────────────────────────────────────────────────┐
│                      Main Agent                          │
│   (LangGraph / CrewAI / AutoGen / Custom Loop)          │
└──────────────────────┬──────────────────────────────────┘
                       │ proposes tool call
                       ▼
┌─────────────────────────────────────────────────────────┐
│              Framework Adapter (e.g. langgraph.attach)  │
│  Intercepts every tool invocation before execution      │
└──────────────────────┬──────────────────────────────────┘
                       │ DecisionContext
                       ▼
┌─────────────────────────────────────────────────────────┐
│                   Sidecar Core                           │
│                                                          │
│  1. Policy Advisor   ─── YAML allow/deny rules          │
│  2. Risk Evaluator   ─── Argument pattern rules         │
│  3. Intent Guardian  ─── Constraint binding check       │
│  4. Budget Guardian  ─── Cost / token ceiling           │
│  5. Plan Evaluator   ─── Multi-step plan review (opt-in)│
│  6. Critic Evaluator ─── Assumption challenge (opt-in)  │
│  7. Judge Evaluator  ─── LLM decision review (opt-in)   │
│                                                          │
│  Returns: Decision(status, risk, reason, ...)           │
└──────────────────────┬──────────────────────────────────┘
                       │ Decision
                       ▼
┌─────────────────────────────────────────────────────────┐
│                   Adapter Enforcement                    │
│                                                          │
│  Observe mode → always passes through, logs decision    │
│  Govern mode  → BLOCK raises SidecarBlockedError        │
│               → PAUSE requires escalation handler       │
└─────────────────────────────────────────────────────────┘
```

---

## Decision Gate pipeline

The Sidecar evaluates modules in a fixed order, short-circuiting at the first BLOCK:

1. **Policy Advisor** — checked first; a `deny` rule immediately returns `BLOCK`
2. **Risk Evaluator** — if risk ≥ `risk_block_threshold` (default: HIGH), returns `BLOCK`
3. **Intent Guardian** — if a constraint binding is violated, returns `BLOCK` or `WARN`
4. **Budget Guardian** — if cost or token ceiling exceeded, returns `PAUSE`
5. **Plan Evaluator** — if plan is unsafe, returns `BLOCK` or `REPLAN`
6. **Critic Evaluator** — if unsupported assumptions detected, returns `CHALLENGE`
7. **Judge Evaluator** — LLM-based review, can return `BLOCK`, `CHALLENGE`, `WARN`, `PAUSE`

If none of the above trigger, the decision is `ALLOW` (or `WARN` if intent drifted but not blocked).

---

## Package boundaries

The codebase is divided into strict layers that never import upward:

| Package | Responsibility | Dependencies |
|---|---|---|
| `core/` | `Sidecar`, `Decision`, `DecisionContext`, `SidecarBlockedError` | None (zero external deps) |
| `gate/` | `PolicyAdvisor`, `RiskEvaluator`, `BudgetGuardian`, `EscalationHandler` | `core/` only |
| `intent/` | `IntentEnvelope`, `IntentGuardian`, `ConstraintBinding` | `core/` only |
| `evaluators/` | `CriticEvaluator`, `JudgeEvaluator`, `PlanEvaluator` | `core/` only |
| `status/` | `StatusNarrator`, `StatusNarrative` | `core/` only |
| `adapters/` | `langgraph.attach`, `crewai`, `autogen`, etc. | `core/`, framework-specific |
| `cli/` | `agentic-sidecar status/version/demo` | `core/`, `status/` |
| `integrations/` | Optional cross-package bridges | `core/`, optional extras |

`core/` must never import from `adapters/` — routing tool calls through `evaluate()` is the adapter's job, not core's.

---

## Operating modes

### Observe mode (default)

```python
sidecar = Sidecar(on_sidecar_failure="fail_closed", mode="observe")
```

- Every tool call is intercepted and evaluated
- `Decision` is computed and logged
- The tool **always executes** regardless of the verdict
- `sidecar.decisions` accumulates every (context, decision) pair for audit

Use this for: shadow auditing, baseline evaluation, initial deployment.

### Govern mode

```python
sidecar = Sidecar(on_sidecar_failure="fail_closed", mode="govern")
```

- Every tool call is intercepted and evaluated
- A `BLOCK` verdict causes the adapter to raise `SidecarBlockedError` **before the tool runs**
- `ALLOW` and `WARN` still pass through (`WARN` is advisory)
- `PAUSE` requires an escalation handler to be registered

Use this for: production enforcement, financial boundary control, safety gating.

---

## Failure handling

`on_sidecar_failure` is a **required** parameter with no default. If the evaluation itself raises an exception (e.g. a misconfigured rule), the Sidecar resolves the decision via this setting:

- `"fail_closed"` — resolves to `BLOCK` (recommended for production)
- `"fail_open"` — resolves to `ALLOW` (use only when you explicitly accept the risk)

This is Design Constraint 3: anything that reaches a Decision Gate is, by definition, worth being conservative about.

---

## Provenance and audit trail

Every call to `sidecar.evaluate()` is recorded in `sidecar.decisions` as a `(DecisionContext, Decision)` tuple. The `Decision` object carries:

- `status` — ALLOW / WARN / BLOCK / CHALLENGE / REPLAN / PAUSE / ESCALATE
- `risk` — LOW / MEDIUM / HIGH (or None if risk evaluator not enabled)
- `reason` — human-readable explanation of the verdict
- `decision_point` — always `"tool_call"` in v0.6
- `trigger_details` — dict with `tool_name` and `arguments`
- `escalation_required` — bool, true for PAUSE/ESCALATE
