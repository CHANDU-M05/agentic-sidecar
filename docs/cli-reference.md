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

Display the current Sidecar status — objective, steps completed, decisions blocked/paused, risk, and budget.

```bash
agentic-sidecar status [OPTIONS]
```

**Options:**

| Option | Short | Description |
|---|---|---|
| `--follow` | `-f` | Follow live status stream, refreshing every `--interval` seconds |
| `--json` | `-j` | Output as JSON instead of a human-readable table |
| `--interval N` | `-i N` | Refresh interval in seconds when `--follow` is enabled (default: 1) |

**Examples:**

```bash
# One-time status snapshot
agentic-sidecar status

# Live stream (Ctrl+C to stop)
agentic-sidecar status --follow

# Live stream, JSON output
agentic-sidecar status --follow --json

# Custom refresh interval
agentic-sidecar status --follow --interval 5
```

**Sample output (table mode):**

```
             Sidecar Status              
┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┓
┃ Metric             ┃ Value           ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━┩
│ 📋 Objective       │ Resolve dispute │
│ ✅ Completed Steps │ 3               │
│ 📞 Tool Calls      │ 3               │
│ 🚫 Blocked         │ 1               │
│ 💰 Budget Remaining│ $4.92           │
└────────────────────┴─────────────────┘
```

**Sample output (JSON mode):**

```json
{
  "timestamp": "2026-09-30T10:15:00",
  "objective": "Resolve dispute",
  "current_step": null,
  "steps_completed": 3,
  "tool_calls": 3,
  "blocked_decisions": 1,
  "paused_decisions": 0,
  "intent_violations": 0,
  "max_risk": "HIGH",
  "budget_remaining": 4.92,
  "tokens_remaining": null,
  "is_paused": false,
  "pause_reason": null
}
```

> **Note (v0.6):** `agentic-sidecar status` currently creates a demo `StatusNarrator` instance. Connecting to a live running `Sidecar` via IPC or HTTP is planned for v0.7.

---

### `version`

Print the installed package version.

```bash
agentic-sidecar version
# agentic-sidecar 0.6.0
```

---

### `demo`

Run an interactive demonstration of the `StatusNarrator` with simulated tool calls.

```bash
agentic-sidecar demo
```

This shows how the CLI status output looks with a live agent — it does not require a running agent.

---

## Status fields reference

| Field | Description |
|---|---|
| `objective` | Top-level task goal set via `narrator.set_objective()` |
| `current_step` | Current step description (if provided to `get_status()`) |
| `steps_completed` | Total tool calls recorded |
| `tool_calls` | Same as `steps_completed` in v0.6 |
| `blocked_decisions` | Number of `BLOCK` decisions since last reset |
| `paused_decisions` | Number of `PAUSE` decisions since last reset |
| `intent_violations` | Number of intent drift events |
| `max_risk` | Highest risk level seen (LOW / MEDIUM / HIGH) |
| `budget_remaining` | USD remaining (only if `current_budget_remaining` passed to `get_status()`) |
| `tokens_remaining` | Tokens remaining (only if `current_tokens_remaining` passed) |
| `is_paused` | Whether execution is currently paused |
| `pause_reason` | Reason for the current pause |
