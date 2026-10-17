# CLI Reference

Agentic Sidecar ships a command-line interface accessible as `agentic-sidecar`.

```
agentic-sidecar --help
```

---

## Installation

The CLI is included with the main package:

```bash
pip install agentic-sidecar
agentic-sidecar --help
```

---

## Commands

### `status`

With --endpoint, display actual task state and lifecycle events from OperatorServer.
Without --endpoint, display the standalone narrator snapshot.

```bash
agentic-sidecar status [OPTIONS]
```

**Options:**

| Option | Short | Description |
|---|---|---|
| `--follow` | `-f` | Repeat the local snapshot every `--interval` seconds |
| `--json` | `-j` | Output as JSON instead of a human-readable table |
| `--endpoint URL` | Runtime HTTP task endpoint (or SIDECAR_ENDPOINT) |
| `--interval N` | `-i N` | Refresh interval in seconds when `--follow` is enabled (default: 1) |

**Examples:**

```bash
# One-time status snapshot
agentic-sidecar status

# Repeat local snapshot (Ctrl+C to stop)
agentic-sidecar status --follow

# Repeated formatted JSON display
agentic-sidecar status --follow --json

# Custom refresh interval
agentic-sidecar status --follow --interval 5
```

**Sample output (`status --json`):**

```json
{
  "timestamp": "2026-10-10T10:00:00",
  "objective": null,
  "current_step": null,
  "steps_completed": 0,
  "tool_calls": 0,
  "blocked_decisions": 0,
  "paused_decisions": 0,
  "intent_violations": 0,
  "max_risk": null,
  "budget_remaining": null,
  "tokens_remaining": null,
  "is_paused": false,
  "pause_reason": null
}
```

Timestamp varies. `--follow --json` includes headings and formatted JSON;
it is a display stream, not JSONL. Use a positive `--interval` value.

---

### `version`

Print the installed package version.

```bash
agentic-sidecar version
# agentic-sidecar 0.8.1
```

---

### `demo`

Run an interactive demonstration of the `StatusNarrator` with simulated tool calls.

```bash
agentic-sidecar demo
```

This populates a local narrator with simulated calls and illustrates terminal
formatting without an agent or API key.

---

## Status fields reference

| Field | Description |
|---|---|
| `objective` | Top-level task goal set via `narrator.set_objective()` |
| `current_step` | Current step description (if provided to `get_status()`) |
| `steps_completed` | Recorded calls, including blocked/paused proposals |
| `tool_calls` | Same as `steps_completed` in v0.6 |
| `blocked_decisions` | Number of supplied BLOCK decisions in this narrator |
| `paused_decisions` | Number of supplied PAUSE decisions in this narrator |
| `intent_violations` | Calls marked `intent_compliant=False` by the application |
| `max_risk` | Highest risk level seen (LOW / MEDIUM / HIGH) |
| `budget_remaining` | USD remaining (only if `current_budget_remaining` passed to `get_status()`) |
| `tokens_remaining` | Tokens remaining (only if `current_tokens_remaining` passed) |
| `is_paused` | Narrator pause state, set by application code |
| `pause_reason` | Reason for the current pause |

## `approval-demo`

Try the local approval prompt without executing a tool:

```bash
agentic-sidecar approval-demo
```

Responses include approve_once, reject (default), modify_intent,
ask_agent_to_replan and stop_agent. For actual governed calls, pass
CLIApprovalHandler from agentic_sidecar.cli.approval as escalation_handler.
See [Governance](governance.md).

## Runtime connection and controls

Use `--endpoint` (or `SIDECAR_ENDPOINT`) to connect `status --follow` to a real
TaskRuntime/OperatorServer. Set `SIDECAR_OPERATOR_TOKEN` in the operator terminal.
`control ACTION` supports pause, resume, stop, restart and replan.
`approve DECISION_ID ACTION` resolves a pending request; `--intent-file FILE`
supplies a complete JSON envelope for modify_intent. See
[Live operations](live-operations.md) for setup, protocol and access scope.
