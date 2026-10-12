# Live operations — 0.7.0

Sidecar now owns a task-local runtime event journal. The LangGraph adapter records
proposals, decisions, actual dispatch reservations, completions and failures.
Evaluation alone never reports successful execution. Local operator controls run
independently of the Judge and use the same runtime as approval resolution.

## Connect a real task

```python
import os
from pathlib import Path
from agentic_sidecar import EventJournal, OperatorServer, Sidecar, TaskRuntime
from agentic_sidecar.adapters.langgraph import attach

runtime = TaskRuntime(journal=EventJournal("order-task", Path("order-task.jsonl")))
sidecar = Sidecar(
    on_sidecar_failure="fail_closed", mode="govern", runtime=runtime,
    escalation_handler=runtime,
)

def read_order(order_id: str) -> str:
    return order_id

with OperatorServer(
    runtime, token=os.environ["SIDECAR_OPERATOR_TOKEN"], actor="local-operator",
) as server:
    print(server.url)
    # Keep this context alive for the lifetime of your agent/graph.
    tools = attach(sidecar, [read_order])
    read_order_tool = tools[0]
    read_order_tool("order-123")
```

Generate a secret of at least 32 characters locally, set `SIDECAR_OPERATOR_TOKEN`
in the application and operator terminal, and keep it out of URLs. Open the
printed task URL for the Control Room and enter the token. The UI displays the
objective, supplied plan, measured intent findings, risk, budget, action lifecycle
and audit events. It exposes pause, resume, stop, explicit restart, intent editing,
replan, and all five per-decision approval actions. The actor is configured by the
server, not trusted from request bodies.

```bash
export SIDECAR_ENDPOINT=http://127.0.0.1:PORT/tasks/order-task
agentic-sidecar status --follow
agentic-sidecar status --follow --json
agentic-sidecar control pause
agentic-sidecar control resume
agentic-sidecar control stop
agentic-sidecar approve DECISION_ID approve_once
agentic-sidecar approve DECISION_ID reject
agentic-sidecar approve DECISION_ID modify_intent --intent-file intent.json
```

`status` without an endpoint retains the standalone narrator demonstration.
With an endpoint it reads real runtime status and new events using a sequence
cursor. `--json` prints formatted JSON snapshots, not JSONL. The live human
narration identifies proposed, blocked, paused, suspended, executed, completed
and failed actions. `completed` counts successful tool returns, not proposals.
A model hook can replace gate stages; missing alignment/risk is reported as
not evaluated rather than invented. Intent findings describe explicit constraint
checks, not a general semantic proof of alignment.

## Local protocol and isolation

The server binds only to `127.0.0.1`; no TLS or public deployment is provided.
Each server holds one task, one token and one configured actor. Use a separate
secret/server per operator trust boundary. Every API read and mutation requires
`Authorization: Bearer TOKEN`. The HTML shell contains no task data or token.
There is no CORS access; cross-origin API requests are rejected. Audit files
contain tool arguments and intent context: protect their filesystem access.
Tools/context must support Pydantic JSON serialization for export.

All routes are prefixed by `/tasks/TASK_ID`:

| Method and suffix | Result |
| --- | --- |
| GET `/status` | Objective, intent, plan, findings, budget, actions, pending approvals, running calls, counters |
| GET `/events?after=N` | Immutable events strictly after sequence N |
| POST `/control` | `{"action":"pause\|resume\|stop\|restart\|replan"}`; submit one action string |
| POST `/approval` | `decision_id`, `action`, optional `modified_intent` and `explanation` |
| POST `/intent` | `{"intent":{...}}` containing a complete IntentEnvelope |

Unknown tasks are rejected. Approval IDs must identify an unresolved request in
this runtime; duplicate/replayed answers are rejected. Approve-once authorizes
one dispatch; authorization is bound to an immutable fingerprint of the evaluated
context, and changed or consumed proposals cannot dispatch. Modify-intent validates
a complete envelope, preserves bindings, and reevaluates the paused proposal.
Runtime intent approvals apply the validated envelope, record the approving actor
and invalidate earlier verdicts before acknowledgement. Direct intent editing also
invalidates earlier verdicts. Approval waiting times out
into REPLAN, including with fail_open. The harness handles replanning and retries;
the operator replan control pauses further dispatch until explicit resume.

## Stop, cancellation and access revocation

Pause/stop share a lock with dispatch reservations. Stop latches before writing
the stop event or invoking external callbacks, independently of evaluation,
approval and failure policy. Once the latch is effective, queued proposals,
approval retries and concurrently evaluated verdicts cannot dispatch. Epochs
invalidate pre-stop/pre-pause decisions, including after explicit restart.
Stop applies to wrapped dispatch in Observe as well as Govern. A broken audit
sink cannot prevent access-revocation callbacks; stop receipts report audit_error
when stop evidence could not be persisted.

Already-dispatched synchronous tools may complete and retain their side effects.
A dispatch event marks admission to execution; stop does not reverse that
admission. Async tools run as owned asyncio tasks and receive cancellation
requests on their own event loop. Cancellation is cooperative: tools can suppress
it. Completion/failure evidence records what actually happened; a request to
cancel is never reported as a completed cancellation. External harnesses can
supply a cancellation callback to `runtime.dispatch(..., cancel=callback)`.

Credential/MCP/session/delegation access belongs to its issuer or gateway. Supply
named `TaskRuntime(revokers={"gateway": revoke_task_access})` callbacks when the
harness grants such access. Each callback must synchronously revoke the root
task's access **and all its sessions and delegated task access**, and return
exactly `True` only after that issuer acknowledges the revocation. Exceptions,
False and other values produce partial failure. The stop receipt reports
`effective_at`, already-running IDs, cancellation requests, per-issuer results,
and `access_revocation`: acknowledged, partial_failure, or not_configured.
`not_configured` acknowledges only the local dispatch stop, never credential
revocation. Revocation failures and in-flight revocations prevent restart.

Explicit restart requires a stopped, idle task and successful configured
revocations; it creates a new decision epoch. It does not renew credentials.
Unwrapped functions and independently created task runtimes remain outside this
boundary. Cross-process isolation and protected-tool gateways are v0.8 work;
a callback contract is not a built-in MCP credential manager. Lens integrity
integration and formal authority handoff remain later milestones.

## Audit snapshots and restoration

Every event has sequence, event_id, task_id, UTC timestamp, kind, payload,
previous_hash and digest. Decision events contain the frozen JSON decision,
trigger, rationale/findings, injected context, proposal_id, policy content/hash,
parent decision link and optional parent_plan_step. Supply
`DecisionContext(parent_decision_id=..., parent_plan_step=...)` when evaluating
steps from a parent plan. Approval records contain actor, action and decision ID;
the resolved decision's causal_link points to the original paused decision.
Dispatch/completion records share invocation_id and decision_id.

`RuntimeEvent` is frozen and stores payload as JSON text. Export returns fresh
nested objects, so mutating exported data or input arguments cannot rewrite the
journal. The older public `sidecar.decisions` list and caller-created AuditRecord
remain compatibility surfaces; the journal is the execution evidence.

The optional JSONL sink writes and fsyncs before publishing an event. New files
use mode 0600; use one writer per task/file. Sink failure follows the configured failure policy. fail_closed prevents dispatch;
fail_open permits execution with missing evidence and reports audit_errors in
status. Stop and stale/consumed decision guards remain enforced independently.
`EventJournal(task_id, path)` restores and checks sequence, identity and hashes.
Malformed partial records and corruption within the retained chain fail restoration.
Removing complete trailing records leaves a valid chain and cannot be detected
without an external trusted head/length checkpoint, which is not provided here.
Hash chaining also cannot detect malicious rewriting by a file owner.
Restored runtimes are stopped and require explicit restart. Uncompleted dispatches
and partial/unacknowledged revocations remain visible and prevent restart;
resolve them in the owning harness rather than claiming completion after a crash.
In a live process, completion/failure always clears running state and cancellation
callbacks, even if writing the final audit event fails. The sink error still
propagates under fail_closed; a later restore may retain unresolved execution
when that final event is missing.

### AI Operations Specification mapping

This is a native Sidecar artifact, not a new normative AIOS schema. Align with
AIOS occurrence/event/evidence conventions, preserving these distinctions:

| Sidecar field | AIOS meaning |
| --- | --- |
| task_id | Producer task correlation; map to the owning Run through explicit deployment attribution |
| decision_id / invocation_id | Distinct supervision and tool-execution occurrences |
| event_id / sequence / timestamp | Producer event identity, ordering and occurrence time |
| causal_link / parent_plan_step | Evidenced causality/plan context; correlation alone is not a causal edge |
| proposed / decision | Proposed work and supervision outcome, not completed execution |
| executed / completed / failed | Dispatch admission and actual tool outcome |
| actor / approval / stop_acknowledged | Operator evidence and access-boundary acknowledgement |

AIOS v0.4 remains an exploratory draft; no formal schema-conformance claim is
made. Control Tower's native `decision` reader accepts the decision inside an
audit event. Attribute it using EvidenceLink with source `agentic-sidecar`, its
source version, registered deployment ID and artifact reference. BLOCK/PAUSE and
other governance outcomes stay separate from deployment health and heartbeat.

## Reproducible acceptance evidence

```bash
uv run pytest tests/test_operations.py
uv run python examples/v0_7_control_room.py
uv run python examples/v0_7_control_room.py --record /tmp/sidecar-recording.json
# For browser operation, configure the token first:
uv run python examples/v0_7_control_room.py --interactive
# Optional local sibling readback, no sibling dependency added to Sidecar:
PYTHONPATH=../agenticops-control-tower/src uv run pytest tests/validation/test_control_tower_native.py
```

The committed `tests/validation/v0_7_lifecycle.json` records one actual HTTP
approval and refund dispatch/completion, followed by a rejection with no second
side effect. Tests cover immutable export/restore, corruption, stop/retry/concurrent
proposals, already-running calls, async cancellation, partial revocation,
issuer-contract session/delegation denial, auth/task isolation, CLI readback,
causal links, approval timeout, and native Control Tower outcome/health separation.
Authenticated OpenAI/Anthropic smoke remains pending credentials, by request;
this limitation is independent of the local operator acceptance evidence.
