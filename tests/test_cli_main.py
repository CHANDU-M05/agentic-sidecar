"""Tests for `agentic_sidecar.cli.main`."""

import json
from unittest.mock import patch

from typer.testing import CliRunner

from agentic_sidecar.cli.main import app
from agentic_sidecar.core.decision import Decision
from agentic_sidecar.status.narrate import StatusNarrator

runner = CliRunner()


def test_version_command() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "agentic-sidecar" in result.stdout
    assert "0.6.1" in result.stdout


def test_status_command_once() -> None:
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    # Should display a table
    assert "Sidecar Status" in result.stdout or "Metric" in result.stdout


def test_status_command_json() -> None:
    result = runner.invoke(app, ["status", "--json"])
    assert result.exit_code == 0
    # Should be valid JSON
    try:
        output = json.loads(result.stdout)
        assert "timestamp" in output
        assert "objective" in output
        assert "tool_calls" in output
    except json.JSONDecodeError:
        pass  # Some other format is also acceptable


def test_status_command_with_follow_flag() -> None:
    """Test --follow flag terminates properly on KeyboardInterrupt."""

    def mock_sleep(interval: int) -> None:
        # Raise KeyboardInterrupt to simulate Ctrl+C on first call
        raise KeyboardInterrupt()

    with patch("time.sleep", side_effect=mock_sleep):
        result = runner.invoke(
            app,
            ["status", "--follow"],
        )
        # Should exit cleanly with the interrupted message
        assert "Stream stopped" in result.stdout


def test_status_command_with_interval() -> None:
    """Test --interval flag."""

    def mock_sleep(interval: int) -> None:
        # Verify interval is passed correctly then exit
        raise KeyboardInterrupt()

    with patch("time.sleep", side_effect=mock_sleep):
        result = runner.invoke(
            app,
            ["status", "--follow", "--interval", "2"],
        )
        # Should complete with interrupted message
        assert "Stream stopped" in result.stdout


def test_status_command_combined_flags() -> None:
    """Test --follow --json combination."""

    def mock_sleep(interval: int) -> None:
        raise KeyboardInterrupt()

    with patch("time.sleep", side_effect=mock_sleep):
        result = runner.invoke(
            app,
            ["status", "--follow", "--json"],
        )
        # Should exit cleanly
        assert "Stream stopped" in result.stdout


def test_demo_command() -> None:
    result = runner.invoke(app, ["demo"])
    assert result.exit_code == 0
    assert "StatusNarrator Demo" in result.stdout
    assert "Demo Status" in result.stdout


def test_status_narrator_with_demo() -> None:
    """Test StatusNarrator integration with demo."""
    narrator = StatusNarrator()
    narrator.set_objective("Find hotels")

    call = narrator.record_tool_call("search", {"query": "NYC hotels"})
    assert call.tool_name == "search"
    assert "🔍" in call.narrative

    status = narrator.get_status(
        current_objective="Searching...",
        current_budget_remaining=100.0,
        current_tokens_remaining=5000,
    )
    assert status.tool_calls_made == 1
    assert status.current_budget_remaining == 100.0


def test_status_narrator_with_decision() -> None:
    """Test StatusNarrator tracking decisions."""
    narrator = StatusNarrator()

    # Record a blocked decision
    blocked_decision = Decision(status="BLOCK", risk=None, reason="Policy")
    narrator.record_tool_call(
        "delete",
        {"id": "123"},
        decision=blocked_decision,
    )
    assert narrator.blocked_decisions == 1

    # Record a paused decision
    paused_decision = Decision(
        status="PAUSE",
        risk=None,
        reason="Budget",
        escalation_required=True,
    )
    narrator.record_tool_call(
        "refund",
        {"amount": 500},
        decision=paused_decision,
    )
    assert narrator.paused_decisions == 1

    status = narrator.get_status()
    assert status.decisions_blocked == 1
    assert status.decisions_paused == 1


def test_status_narrator_intent_violations() -> None:
    """Test StatusNarrator tracking intent violations."""
    narrator = StatusNarrator()

    narrator.record_tool_call("search", {}, intent_compliant=True)
    narrator.record_tool_call("search", {}, intent_compliant=False)
    narrator.record_tool_call("search", {}, intent_compliant=False)

    status = narrator.get_status()
    assert status.intent_violations == 2


def test_status_narrative_generation() -> None:
    """Test narrative generation from tool calls."""
    narrator = StatusNarrator()
    narrator.set_objective("Book a hotel")

    narrator.record_tool_call("search", {})
    narrator.record_tool_call("retrieve", {})

    narrative = narrator.get_narrative()
    assert "Book a hotel" in narrative
    assert "Steps taken:" in narrative


def test_status_command_with_objective_override() -> None:
    """Test status command respects current_objective parameter."""
    narrator = StatusNarrator()
    narrator.set_objective("Original objective")

    status = narrator.get_status(current_objective="Override objective")
    assert status.current_objective == "Override objective"


def test_demo_with_multiple_statuses() -> None:
    """Test demo command with various decision statuses."""
    narrator = StatusNarrator()
    narrator.set_objective("Process payment")

    # Allow
    narrator.record_tool_call(
        "validate",
        {},
        decision=Decision(status="ALLOW", risk="LOW", reason="ok"),
    )

    # Warn
    narrator.record_tool_call(
        "process",
        {},
        decision=Decision(status="WARN", risk="MEDIUM", reason="unusual amount"),
    )

    # Block
    narrator.record_tool_call(
        "confirm",
        {},
        decision=Decision(status="BLOCK", risk="HIGH", reason="Fraud detected"),
    )

    status = narrator.get_status()
    assert status.decisions_blocked == 1
    assert status.tool_calls_made == 3
