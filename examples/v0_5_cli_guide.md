# CLI Guide

This guide targets **0.6.1**. The filename records the CLI's introduction in 0.5.
The CLI includes local status display, simulated narration, package version,
and a local approval prompt.

```bash
uv sync --extra dev
uv run agentic-sidecar --help
uv run agentic-sidecar version
# agentic-sidecar 0.6.1
```

## Local status snapshots

```bash
uv run agentic-sidecar status
uv run agentic-sidecar status --json
uv run agentic-sidecar status --follow --interval 2
```

Each invocation creates a fresh local `StatusNarrator`. A normal snapshot has
zero recorded calls and no objective or budget values. `--follow` repeats that
snapshot at the requested positive interval; use Ctrl+C to stop. Connection to
runtime events is planned for 0.7. `--follow --json` includes stream headings and
formatted JSON, so it is intended for display rather than JSONL ingestion.

## Simulated narration

```bash
uv run agentic-sidecar demo
```

The demo populates a narrator with an objective and three simulated calls.
It illustrates terminal formatting without running an agent or calling APIs.

## Local approval prompt

```bash
uv run agentic-sidecar approval-demo
```

This tries all five approval actions without dispatching a tool. For actual
PAUSE/ESCALATE handling, pass CLIApprovalHandler from agentic_sidecar.cli.approval
as escalation_handler on a Govern Sidecar. See [Governance](../website/docs/governance.md).

## Populate a narrator in your application

```python
from agentic_sidecar import Decision, StatusNarrator

narrator = StatusNarrator()
narrator.set_objective("Review order A100")
narrator.record_tool_call(
    "read_order",
    {"order_id": "A100"},
    decision=Decision(status="ALLOW", risk="LOW", reason="read permitted"),
    risk_level="LOW",
    intent_compliant=True,
)
print(narrator.get_narrative())
status = narrator.get_status(current_budget_remaining=4.50)
print(status.tool_calls_made, status.current_budget_remaining)
```

Decisions, risk, compliance, and budget values are supplied by application code.
`pause()` and `resume()` update narrator state; application code controls actual
execution. `steps_completed` currently counts recorded calls, including blocked
or paused proposals. Creating a narrator in your application does not attach it
to a separate CLI process.

See [CLI reference](../website/docs/cli-reference.md),
[examples](README.md), and [roadmap](../ROADMAP.md).
