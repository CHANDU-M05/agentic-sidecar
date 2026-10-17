# Limitations

Supported scope for the **0.8.0** API. See [Governance](governance.md) for usage
and validation evidence, and [Roadmap](roadmap.md) for future priorities.

## Governance boundary

Observe records verdicts and executes tools. Govern executes ALLOW/WARN only;
BLOCK raises SidecarBlockedError. PAUSE/ESCALATE invoke a registered handler or
raise SidecarSuspendedError when unresolved. CHALLENGE/REPLAN always return
control through SidecarSuspendedError. These exceptions prevent the tool call;
they do not checkpoint, resume, or replan an entire agent workflow.

Approval is local or supplied through the authenticated runtime HTTP interface. Async tools run
evaluation/approval in a worker thread to avoid blocking their event loop.
Cancelling the waiting coroutine cannot cancel a running sync evaluator/prompt.
Use one Sidecar/Judge/Budget per task. Runtime approvals support concurrent
proposals; evaluators and manual budget accounting are not a task transaction.

APPROVE_ONCE authorizes the current invocation only. BLOCK cannot be approved.
MODIFY_INTENT requires a full envelope, preserves bindings and reevaluates once;
another intervention returns control without an automatic prompt loop.
STOP_AGENT latches the task; explicit runtime restart is required to run again. REJECT blocks that proposal. REPLAN returns control to the agent loop.

## Deterministic intent and heuristic evaluators

Policy/Risk use ordered tool patterns and argument comparisons. Intent requires
explicit bindings; absent constraints/arguments are skipped. Expiry produces
WARN. Authority bindings and delegated authority are planned for 0.9.

`evaluate_plan()` checks explicit step dictionaries; it does not discover or
execute the agent's plan. Planner uses selected tool/goal patterns, contradictory
tool pairs and supplied constraint bindings. Critic uses selected risky tool
patterns, previously permitted opposing actions and explicit metadata evidence
flags (`authorized`, `eligibility_verified`, `backup_verified`). These flags are
caller-supplied assertions, not independently verified authorization. History
records verdicts, not successful executions. Heuristics do not establish general
semantic intent or proof of correctness; confidence thresholds filter fixed
heuristic scores. Full-plan Critic review conservatively checks each step.

## Live providers and usage accounting

OpenAIJudge and AnthropicJudge make real optional SDK calls. MockJudge is an
explicit offline fixture. Models and current USD token rates are configured by
the caller. Supply both rates for cost ceilings/task budget accounting; without
rates, use cost_limit=None and no BudgetGuardian. Known returned usage is recorded
once; framework/tool usage outside Judge still needs record_invocation().

Judge cost limits apply after a response and cannot reserve future spend.
Provider-native timeouts disable SDK retries. Judge timeout bounds waiting;
an arbitrary sync call cannot be cancelled and may finish after timeout. Late
sync responses still account usage, and another invocation is refused while
one is outstanding. Native async calls are cancelled at timeout; provider spend
without returned usage cannot be recovered from that cancellation. Malformed
outputs with valid usage still account completed inference before verdict
validation. Unknown or invalid usage never creates invented cost measurements.

Live API smoke results require credentials and an explicit model. Normal CI
uses deterministic SDK contract fixtures. See [acceptance evidence](governance.md)
for the recorded live-smoke status.

## Runtime, records and integrations

Failure policy covers injection, evaluator/provider errors, malformed verdicts,
logging/recording and approvals. A failed recorder returns the configured
fallback but cannot guarantee an audit entry -- the already-computed verdict
is discarded, so with `fail_open` a recorder failure after a genuine BLOCK
resolves to ALLOW; `fail_closed` resolves the same failure to BLOCK instead.
A custom before_tool_call hook replaces all built-in stages, including plan
checks, budget and evaluators.

Decision IDs and approval causal links are available. In-memory contexts are
deep-copied at recording time; the public list, its contexts and nested decision
dictionaries remain mutable. The immutable runtime journal records durable execution lifecycle; see
[Live operations](live-operations.md). AuditRecord remains a caller-created export type.

LangGraph sync/async plain callables are supported. Framework-native tool objects,
additional adapters and optional ecosystem exports target 0.8.

## Narration and CLI

The standalone StatusNarrator remains manually populated. Connected CLI status
reads actual runtime events and execution state; `--follow --json` prints
formatted snapshots, not JSONL. The Control Room uses the same authenticated
HTTP interface. See [Live operations](live-operations.md) for task isolation,
stop/cancellation/revocation boundaries and restore behavior.

The package remains Pre-Alpha; stable API/schema guarantees target 1.0.

## Scoped delivery and adapters

v0.8 provides explicit host context delivery and mandatory guardrail composition.
Wrappers cover returned tools only. Private-context isolation across external
memories, outputs and telemetry remains v0.9 validation work; keep journals and
configuration in the trusted host. Semantica export remains conditional. See
[scoped limits](scoped-supervision.md#limits-and-responsibilities) and
[validated framework versions](integrations.md).
