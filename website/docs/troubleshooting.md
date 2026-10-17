# Troubleshooting

Use the returned verdict, enabled roles, and configured bindings to inspect
behavior before attaching real tools. These notes describe the **0.8.0** API.

## Required failure configuration

Omitting `on_sidecar_failure` raises `TypeError`; an unsupported value raises
`ValueError`. Choose `fail_closed` for governed decision boundaries:

```python
from agentic_sidecar import Sidecar
sidecar = Sidecar(on_sidecar_failure="fail_closed")
```

## Optional modules and roles

Enable a module by passing its instance and including its role. Intent checks
also require a configured envelope and bindings. Passing an IntentGuardian
without `intent_guardian` in roles raises ValueError. Other optional modules
should likewise have matching roles:

```python
from agentic_sidecar import BudgetGuardian, Sidecar
budget = BudgetGuardian(max_cost=5)
sidecar = Sidecar(on_sidecar_failure="fail_closed", budget=budget, roles=["budget"])
budget.record_invocation(cost=5)
```

Supported roles: policy, risk, intent_guardian, budget, planner, critic, judge.

## Inspect a BLOCK decision

Policy denial, risk threshold, and intent constraints can each produce BLOCK.
Read the exception's `decision.reason` and `context` to identify the stage.
Test a proposed action directly without dispatching it:

```python
from agentic_sidecar import DecisionContext
verdict = sidecar.evaluate(DecisionContext(tool_name="issue_refund", tool_args={"amount": 850}))
print(verdict.status, verdict.reason)
```

Observe mode permits execution after a verdict. Use it with controlled tools
when evaluating rules; Govern enforces BLOCK through the adapter.

## Budget and approval handling

Judge usage automatically reaches the configured task budget. Record other
calls explicitly. Govern suspends PAUSE/ESCALATE when no handler exists.
Register on_escalation_required or pass CLIApprovalHandler as escalation_handler.
Base EscalationHandler is an interface; it raises NotImplementedError.

## Planner input

Use `Sidecar.evaluate_plan(plan, goal=...)` for a full-plan gate. Configuring a
planner on tool calls does not discover the plan. The active envelope supplies
goal/constraints; all evaluators receive history/plan/metadata.

## Provider configuration

Use MockJudge for offline scripted examples. OpenAIJudge/AnthropicJudge make
live API calls and require their optional SDK, credentials and an explicit model.
Supply both token rates before enabling cost ceilings or a task budget.
Provider errors and timeouts follow on_sidecar_failure; direct Judge calls raise.
See [Governance](governance.md) for setup and [Limitations](limitations.md) for
post-response cost ceilings and cancellation boundaries.

## Local CLI status

`status` starts with a fresh narrator. Zero calls and no objective are expected.
`demo` shows a populated simulated narrator. Creating a narrator in application
code does not connect a separate CLI process. For live status, run an OperatorServer
in the task process and supply its URL through --endpoint or SIDECAR_ENDPOINT;
set the same SIDECAR_OPERATOR_TOKEN in the operator terminal.
Use a positive refresh interval for `--follow`.

## Rule matching

Tool patterns use `fnmatch`, not regular expressions. Rules are ordered;
the first match wins. Argument checks require the exact configured key.

```python
import fnmatch
print(fnmatch.fnmatch("soft_delete", "delete_*"))  # False
print(fnmatch.fnmatch("soft_delete", "*delete*"))  # True
```

Constraint bindings skip undeclared constraints and absent arguments. Bindings
validate the supplied structured values; they do not infer natural-language limits.

## Optional framework and docs setup

The callable wrapper itself does not import LangGraph. To run the real graph
examples, install its extra. To build the site, install the docs extra:

```bash
uv sync --extra dev --extra docs --extra langgraph
uv run mkdocs build --strict
```

For a docs build failure, inspect the first error, verify local links/anchors,
and include new pages in `website/mkdocs.yml` navigation.
