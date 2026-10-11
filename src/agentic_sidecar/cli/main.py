"""Local status reporting and interactive approval commands."""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any

import typer
from rich.console import Console
from rich.progress import Progress
from rich.table import Table

from agentic_sidecar.cli.approval import CLIApprovalHandler
from agentic_sidecar.core.context import DecisionContext
from agentic_sidecar.core.decision import Decision
from agentic_sidecar.gate.escalation import ApprovalAction, EscalationRequest
from agentic_sidecar.status.narrate import StatusNarrative, StatusNarrator

app = typer.Typer(help="Agentic Sidecar CLI - Status reporting and local approvals")
console = Console()


@app.command()
def approval_demo() -> None:
    """Try the local approval prompt without executing a tool or changing a task."""
    decision = Decision(status="PAUSE", risk=None, reason="Demonstration approval request")
    request = EscalationRequest(
        decision.decision_id,
        decision.reason,
        DecisionContext(tool_name="demo").model_dump(mode="json"),
        list(ApprovalAction),
    )
    response = CLIApprovalHandler(console).handle_escalation(request)
    console.print(f"Selected {response.action.value}; no tool executed.")


@app.command()
def status(
    follow: bool = typer.Option(False, "--follow", "-f", help="Repeat the local status snapshot"),
    json_output: bool = typer.Option(
        False, "--json", "-j", help="Output as JSON instead of human-readable format"
    ),
    interval: int = typer.Option(
        1, "--interval", "-i", help="Refresh interval in seconds (when --follow is enabled)"
    ),
) -> None:
    """Display sidecar status: current objective, decisions, risk, and budget.

    With --follow, repeats a local narrator snapshot.
    Use Ctrl+C to stop.

    Examples:
        agentic-sidecar status                    # One-time snapshot
        agentic-sidecar status --follow           # Live stream
        agentic-sidecar status --json             # JSON output
        agentic-sidecar status --follow --json    # Live JSON stream
    """
    narrator = _get_narrator_instance()

    if not follow:
        _display_status_once(narrator, json_output)
    else:
        _display_status_stream(narrator, json_output, interval)


def _get_narrator_instance() -> StatusNarrator:
    """Get the active StatusNarrator instance.

    Runtime connection via IPC or HTTP is planned for v0.7.
    """
    return StatusNarrator()


def _display_status_once(narrator: StatusNarrator, json_output: bool) -> None:
    """Display a single status snapshot."""
    status = narrator.get_status()

    if json_output:
        output = {
            "timestamp": status.timestamp.isoformat(),
            "objective": status.current_objective,
            "current_step": status.current_step,
            "steps_completed": status.steps_completed,
            "tool_calls": status.tool_calls_made,
            "blocked_decisions": status.decisions_blocked,
            "paused_decisions": status.decisions_paused,
            "intent_violations": status.intent_violations,
            "max_risk": status.max_risk_seen,
            "budget_remaining": status.current_budget_remaining,
            "tokens_remaining": status.current_tokens_remaining,
            "is_paused": status.is_paused,
            "pause_reason": status.pause_reason,
        }
        console.print_json(data=output)
    else:
        _print_status_table(status)


def _display_status_stream(narrator: StatusNarrator, json_output: bool, interval: int) -> None:
    """Display a live status stream with periodic updates."""
    console.print("[bold cyan]🔴 Live Status Stream[/bold cyan]")
    console.print(f"Refreshing every {interval}s — Press Ctrl+C to stop\n")

    try:
        iteration = 0
        while True:
            iteration += 1

            if json_output:
                status = narrator.get_status()
                output = {
                    "iteration": iteration,
                    "timestamp": status.timestamp.isoformat(),
                    "objective": status.current_objective,
                    "current_step": status.current_step,
                    "steps_completed": status.steps_completed,
                    "tool_calls": status.tool_calls_made,
                    "blocked_decisions": status.decisions_blocked,
                    "paused_decisions": status.decisions_paused,
                    "intent_violations": status.intent_violations,
                    "max_risk": status.max_risk_seen,
                    "budget_remaining": status.current_budget_remaining,
                    "tokens_remaining": status.current_tokens_remaining,
                    "is_paused": status.is_paused,
                    "pause_reason": status.pause_reason,
                }
                console.print_json(data=output)
            else:
                status = narrator.get_status()
                _print_status_table(status)
                console.print(f"[dim]Updated at {datetime.now().strftime('%H:%M:%S')}[/dim]\n")

            time.sleep(interval)

    except KeyboardInterrupt:
        console.print("\n[yellow]⏸️  Stream stopped by user[/yellow]")


def _print_status_table(status: StatusNarrative) -> None:
    """Print a formatted status table."""
    table = Table(title="Sidecar Status", show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    # Objective
    if status.current_objective:
        table.add_row("📋 Objective", status.current_objective)

    # Current step
    if status.current_step:
        table.add_row("⚙️ Current Step", status.current_step)

    # Progress
    table.add_row("✅ Completed Steps", str(status.steps_completed))
    table.add_row("📞 Tool Calls", str(status.tool_calls_made))

    # Decisions
    if status.decisions_blocked > 0:
        table.add_row("🚫 Blocked", f"[red]{status.decisions_blocked}[/red]")
    if status.decisions_paused > 0:
        table.add_row("⏸️ Paused", f"[yellow]{status.decisions_paused}[/yellow]")

    # Intent
    if status.intent_violations > 0:
        table.add_row("⚠️ Intent Violations", f"[yellow]{status.intent_violations}[/yellow]")

    # Risk
    if status.max_risk_seen:
        risk_color = "red" if status.max_risk_seen == "HIGH" else "yellow"
        table.add_row("⚠️ Max Risk", f"[{risk_color}]{status.max_risk_seen}[/{risk_color}]")

    # Budget
    if status.current_budget_remaining is not None:
        table.add_row("💰 Budget Remaining", f"${status.current_budget_remaining:.2f}")
    if status.current_tokens_remaining is not None:
        table.add_row("🔤 Tokens Remaining", str(status.current_tokens_remaining))

    # Pause status
    if status.is_paused:
        pause_text = status.pause_reason or "Awaiting approval"
        table.add_row("⏸️ Status", f"[yellow]PAUSED: {pause_text}[/yellow]")

    console.print(table)


@app.command()
def version() -> None:
    """Show agentic-sidecar version."""
    from agentic_sidecar import __version__

    console.print(f"agentic-sidecar {__version__}")


@app.command()
def demo() -> None:
    """Run an interactive demo of the status narrator.

    Shows how the CLI would work with a live agent.
    """
    console.print("[bold cyan]🎬 StatusNarrator Demo[/bold cyan]\n")

    narrator = StatusNarrator()
    narrator.set_objective("Find and book the cheapest hotel in NYC")

    demo_steps: list[tuple[str, dict[str, Any], str]] = [
        ("search", {}, "🔍 Searching for information"),
        ("query", {}, "❓ Querying database"),
        ("retrieve", {}, "📥 Retrieving records"),
    ]

    with Progress() as progress:
        task = progress.add_task("[cyan]Executing demo...", total=len(demo_steps))

        for tool, args, _expected_narration in demo_steps:
            call = narrator.record_tool_call(tool, args)
            console.print(f"  {call.narrative}")
            progress.update(task, advance=1)
            time.sleep(0.5)

    console.print("\n[bold green]Demo Status:[/bold green]")
    status = narrator.get_status(
        current_objective="Booking hotel...",
        current_budget_remaining=25.50,
        current_tokens_remaining=4500,
    )
    _print_status_table(status)


def main() -> None:
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
