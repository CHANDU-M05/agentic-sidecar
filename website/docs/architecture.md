# Architecture

**The Main Agent acts. The Sidecar observes, thinks, advises, and governs.**
Sidecar evaluates proposed actions; the agent runtime and adapter own execution.

## Decision flow

```text
Agent proposes an action
  → LangGraph callable wrapper or caller-managed boundary
  → DecisionContext
  → Sidecar: Policy → Risk → Intent → Budget → Planner → Critic → Judge
  → Decision
  → Observe: call through
  → Govern: ALLOW/WARN execute; BLOCK stops; other outcomes resolve or suspend
```

Modules run only when enabled in `roles` and configured. A policy denial, risk
threshold, or blocking intent finding returns immediately. Budget PAUSE,
planner REPLAN/BLOCK, Critic CHALLENGE, and supported Judge interventions also
return before later stages. Intent WARN is advisory and can accompany later
checks. A custom `before_tool_call` hook replaces the built-in pipeline.

Use `Sidecar.evaluate_plan()` for full-plan review before dispatch. Evaluators
receive goal, constraints, intent, decision history, plan and metadata. Planner
and Critic are deterministic heuristics; Judge uses an explicit MockJudge or
optional live provider. See [Governance](governance.md).

## Operating modes

| Mode | Adapter behavior |
| --- | --- |
| Observe (default) | Computes/logs verdicts, then executes the wrapped tool |
| Govern | ALLOW/WARN execute; BLOCK stops; PAUSE/ESCALATE invoke approvals; unresolved outcomes suspend |

Budget ceilings produce PAUSE. Govern invokes a registered escalation handler
or returns control via SidecarSuspendedError. Approvals are scoped to one call;
BLOCK never reaches approval. CHALLENGE/REPLAN suspend for agent-loop handling.

## Failure configuration

`on_sidecar_failure` is required: `fail_closed` converts caught gate errors to
BLOCK; `fail_open` converts them to ALLOW. Observe remains advisory regardless
of that verdict. Configure `fail_closed` for governed boundaries.

Injection, evaluation/provider calls, verdict validation and recording share
the failure boundary. Approval errors follow the same policy. Judge errors
propagate to that boundary. Recording failures cannot guarantee a log entry;
see [supported scope](limitations.md) for timeout and accounting details.

## Package boundaries

| Package | Responsibility | Current dependencies |
| --- | --- | --- |
| `core/` | Runtime, contexts, decision and provenance types | Gate, intent, evaluators, Pydantic |
| `gate/` | Policy, risk, budget and approval primitives | Core models/operators; Pydantic and PyYAML for rules |
| `intent/` | Envelope and constraint bindings | Core models/operators, Pydantic |
| `evaluators/` | Planner/Critic heuristics, Judge/provider interface | Core types, evaluator base; live SDK imports are lazy and optional |
| `status/` | Manually populated narration | Core decision types |
| `adapters/` | Framework interception | Core; LangGraph callable wrapper has no framework import dependency |
| `cli/` | Local status, approval, demo, version | Status, Typer, Rich |
| `integrations/` | Reserved optional ecosystem bridges | Planned for 0.8 |

`core/` never imports adapters. Policy/Risk stay independent of Intent and
model evaluators. Framework and sibling packages remain optional.

## Decision records and status

`sidecar.decisions` stores in-memory `(DecisionContext, Decision)` pairs.
Built-in verdicts commonly include `decision_point="tool_call"` and trigger
arguments. Hook and failure verdicts may leave those fields unset. `Decision`
is frozen at the field level; nested dictionaries and saved contexts remain
mutable. `AuditRecord.to_dict()` serializes caller-created provenance records.
Contexts are deep-copied at recording time; decisions have IDs and resolved
approvals link to their originating decision. TaskRuntime adds immutable JSON event
snapshots and optional durable JSONL execution evidence.

`StatusNarrator` records application-supplied call/decision metadata. Its pause
state is reporting state. CLI status with --endpoint connects to actual runtime
events. TaskRuntime and OperatorServer provide task-scoped operator controls;
see [Live operations](live-operations.md).
