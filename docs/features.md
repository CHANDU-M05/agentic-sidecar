# Features

Current **0.8.0** capabilities and their supported usage. Upcoming extensions
are described in [Roadmap](roadmap.md); execution boundaries are summarized in
[Limitations](limitations.md).

## Policy Advisor

Deterministic allow/deny rules use ordered `fnmatch` tool patterns. The first
match wins; the configurable default is allow. Load YAML with `from_yaml()`
or use `from_mapping()` / explicit rules:

```python
from agentic_sidecar import DecisionContext
from agentic_sidecar.gate.policy import PolicyAdvisor, PolicyRule

policy = PolicyAdvisor([PolicyRule(tool="delete_*", effect="deny")])
print(policy.evaluate(DecisionContext(tool_name="delete_customer")).effect)  # deny
```

## Risk Evaluator

Ordered tool/argument rules classify LOW, MEDIUM, or HIGH. Sidecar returns
BLOCK when classification reaches `risk_block_threshold` (default HIGH).
Supported comparisons are eq, ne, gt, gte, lt, lte, in, and contains.

```python
from agentic_sidecar import DecisionContext
from agentic_sidecar.gate.risk import RiskEvaluator, RiskRule

risk = RiskEvaluator([RiskRule(
    tool="issue_refund", arg_name="amount", arg_op="gt", arg_value=500, risk="HIGH",
)])
print(risk.evaluate(DecisionContext(tool_name="issue_refund", tool_args={"amount": 850})).risk)
# HIGH
```

## Intent Guardian

IntentEnvelope carries goal, requester, constraints, authority, expiry, and
metadata. ConstraintBinding connects a declared constraint to a tool argument.
Numeric/enum/allow-list checks produce WARN or BLOCK; expiry produces WARN.
Authority bindings target 0.9. See the runnable [Getting Started](getting-started.md)
example and [Configuration](configuration.md).

## Budget Guardian

Record cost/tokens explicitly. A recorded ceiling produces PAUSE when the
budget role is configured. Govern suspends the tool until approval resolution.

```python
from agentic_sidecar import BudgetGuardian, DecisionContext, Sidecar

budget = BudgetGuardian(max_cost=5, max_tokens=10_000)
sidecar = Sidecar(on_sidecar_failure="fail_closed", budget=budget, roles=["budget"])
budget.record_invocation(cost=5, tokens=1200)
print(sidecar.evaluate(DecisionContext(tool_name="read_order")).status)  # PAUSE
```

Judge usage automatically reaches the configured task BudgetGuardian once.
Other framework usage still needs explicit accounting.

## Plan Evaluator

Direct plan review applies selected unnecessary-step and contradiction
heuristics, returning ALLOW or REPLAN. Supply `plan` and `goal` explicitly:

```python
from agentic_sidecar import PlanEvaluator

result = PlanEvaluator().evaluate({
    "goal": "Explain the disputed charge",
    "plan": [{"tool_name": "read_charge"}, {"tool_name": "issue_refund"}],
})
print(result.status)  # REPLAN
```

Use `sidecar.evaluate_plan(plan, goal=...)` to pass a full plan through the
gate, including policy/risk and intent checks per step. Configuring planner
alone does not discover a plan from tool calls.

## Critic Evaluator

Tool-name heuristics identify selected risky actions and assumptions, producing
ALLOW or CHALLENGE. They do not establish contextual authorization by themselves.

```python
from agentic_sidecar import CriticEvaluator, DecisionContext, Sidecar

sidecar = Sidecar(
    on_sidecar_failure="fail_closed", critic=CriticEvaluator(), roles=["critic"],
)
print(sidecar.evaluate(DecisionContext(tool_name="delete_records")).status)  # CHALLENGE
```

Govern suspends CHALLENGE. Critic also checks selected opposing previously
permitted actions and caller-supplied evidence flags; see [Limitations](limitations.md).

## Judge Evaluator

The model-agnostic provider interface accepts decision context and returns
status, rationale, confidence, and usage metadata. MockJudge is offline;
OpenAIJudge/AnthropicJudge use optional live SDKs. This example makes no API call:

```python
from agentic_sidecar import JudgeEvaluator, MockJudge

judge = JudgeEvaluator(provider=MockJudge(model="demo-model"))
result = judge.evaluate({
    "tool_name": "read_order", "arguments": {}, "goal": "Review order A100",
})
print(result.status)  # ALLOW (scripted response)
```

Judge validates verdicts/usage, bounds waiting, accounts sync/async usage and
applies per-call cost ceilings after a response. Provider errors follow Sidecar
failure policy. See [Governance](governance.md) for live provider configuration.

## Status Narrator

Manually record proposals/calls, decisions, risk, compliance, and budget values:

```python
from agentic_sidecar import Decision, StatusNarrator

narrator = StatusNarrator()
narrator.set_objective("Review order A100")
call = narrator.record_tool_call(
    "read_order", {"order_id": "A100"},
    decision=Decision(status="ALLOW", risk="LOW", reason="read permitted"),
    risk_level="LOW", intent_compliant=True,
)
print(call.narrative)  # Executing read_order, with the generic narration prefix
print(narrator.get_status(current_budget_remaining=4.50).tool_calls_made)  # 1
```

Narration matches common tool-name patterns. `pause()` / `resume()` report
state; application code controls execution. CLI status with --endpoint reads the
runtime journal and distinguishes proposed, blocked, paused, executed and completed
actions. See [Live operations](live-operations.md) for the Control Room and controls.

## Human Escalation

ApprovalAction, EscalationRequest, ApprovalResponse, and EscalationHandler define
the request/response contract. Govern invokes a registered handler for
PAUSE/ESCALATE and validates response IDs/actions. CLIApprovalHandler provides
a local prompt. See [Governance](governance.md) for all five approval actions.

## Custom Decision Hook

`before_tool_call` replaces the ordinary built-in pipeline, including budget and
evaluators. Trusted mandatory scope checks still run before the hook and cannot
be bypassed by its ALLOW verdict.
It receives injected intent/history and returns a Decision:

```python
from agentic_sidecar import Decision, DecisionContext, Sidecar

sidecar = Sidecar(on_sidecar_failure="fail_closed")

@sidecar.before_tool_call
def review(context: DecisionContext) -> Decision:
    status = "BLOCK" if context.tool_name.startswith("delete_") else "ALLOW"
    return Decision(status=status, risk="LOW", reason="Custom rule")

print(sidecar.evaluate(DecisionContext(tool_name="delete_customer")).status)  # BLOCK
```

Use the standard pipeline when you want configured modules to run together.
Provenance export types are documented in [API reference](api-reference.md).

## Shared & Exclusive supervision

`ScopedSystem` binds trusted agent identities to shared and exclusive layers.
Choose context only, guardrails only or both. Context delivery to the host is
explicit; shared denials remain mandatory alongside exclusive restrictions.
Each bound agent has a separate history and copied payload. See
[scoped supervision](scoped-supervision.md) for privacy and deployment limits.

## Native adapters and evidence

v0.8 provides AutoGen, CrewAI, OpenAI Agents, Google ADK and MCP boundaries in
addition to LangGraph. Native SDK conformance covers all seven decisions and
both modes. Verified correlated decisions reach Lens 0.7.1 incident timelines;
Chaos recovery proposals retain native event IDs. See [integrations](integrations.md).
