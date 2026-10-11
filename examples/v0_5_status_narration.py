"""StatusNarrator examples for 0.6.1 (introduced in 0.5).

All decisions, risk/compliance, and budget values are supplied locally.
Pause/resume changes narrator state; no agent is controlled or API called.

Demonstrates:
- StatusNarrator for tracking agent execution
- Human-readable narration of tool calls
- Decision tracking (ALLOW, WARN, BLOCK, PAUSE)
- Risk level monitoring
- Application-supplied intent compliance reporting
- Budget/token tracking
"""

import sys

# Set UTF-8 encoding for proper emoji/unicode display
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from agentic_sidecar import (
    Decision,
    StatusNarrator,
)


def example_basic_narration() -> None:
    """Basic StatusNarrator usage."""
    print("\n=== Basic Status Narration ===\n")

    narrator = StatusNarrator()
    narrator.set_objective("Find the cheapest flight to NYC")

    # Record tool calls with automatic narration
    call1 = narrator.record_tool_call("search", {"query": "flights NYC"})
    print(f"Tool: search → {call1.narrative}")

    call2 = narrator.record_tool_call("retrieve", {"id": "flight_123"})
    print(f"Tool: retrieve → {call2.narrative}")

    call3 = narrator.record_tool_call("compare_prices", {"items": 5})
    print(f"Tool: compare_prices → {call3.narrative}")

    # Display status
    status = narrator.get_status()
    print(f"\nStatus: {status.tool_calls_made} tool calls completed")
    print(f"Narrative:\n{narrator.get_narrative()}")


def example_with_decisions() -> None:
    """StatusNarrator with decision tracking."""
    print("\n=== Status Narration with Decisions ===\n")

    narrator = StatusNarrator()
    narrator.set_objective("Process customer refund")

    # Allowed decision
    decision_allow = Decision(status="ALLOW", risk="LOW", reason="Within policy")
    call1 = narrator.record_tool_call("validate_refund", {"amount": 50}, decision=decision_allow)
    print(f"✓ {call1.narrative} (ALLOW)")

    # Warning decision
    decision_warn = Decision(
        status="WARN", risk="MEDIUM", reason="Unusual amount for this customer"
    )
    call2 = narrator.record_tool_call(
        "check_history", {"customer_id": "c123"}, decision=decision_warn
    )
    print(f"⚠ {call2.narrative} (WARN)")

    # Blocked decision
    decision_block = Decision(status="BLOCK", risk="HIGH", reason="Refund exceeds limit")
    call3 = narrator.record_tool_call("process_refund", {"amount": 1000}, decision=decision_block)
    print(f"✗ {call3.narrative} (BLOCK)")

    # Paused decision (requires escalation)
    decision_pause = Decision(
        status="PAUSE",
        risk="HIGH",
        reason="Budget limit reached",
        escalation_required=True,
    )
    call4 = narrator.record_tool_call("process_refund", {"amount": 500}, decision=decision_pause)
    print(f"⏸ {call4.narrative} (PAUSE)")

    # Status summary
    status = narrator.get_status()
    print(f"\nDecisions: {status.decisions_blocked} blocked, {status.decisions_paused} paused")


def example_with_budget_tracking() -> None:
    """StatusNarrator with budget and token tracking."""
    print("\n=== Status Narration with Budget Tracking ===\n")

    narrator = StatusNarrator()
    narrator.set_objective("Analyze market data and generate report")

    # Simulate tool calls with budget tracking
    calls = [
        ("fetch_market_data", {}),
        ("analyze_trends", {}),
        ("generate_report", {}),
    ]

    for tool, args in calls:
        call = narrator.record_tool_call(tool, args)
        print(f"📊 {call.narrative}")

    # Get status with budget info
    status = narrator.get_status(
        current_objective="Report generation in progress",
        current_budget_remaining=42.50,
        current_tokens_remaining=3500,
    )

    print(f"\n💰 Budget remaining: ${status.current_budget_remaining:.2f}")
    print(f"🔤 Tokens remaining: {status.current_tokens_remaining}")
    print(f"📞 Total tool calls: {status.tool_calls_made}")


def example_intent_compliance() -> None:
    """StatusNarrator tracking intent compliance."""
    print("\n=== Intent Compliance Tracking ===\n")

    narrator = StatusNarrator()
    narrator.set_objective("Send notification to user")

    # Compliant calls
    call1 = narrator.record_tool_call(
        "send_email", {"to": "user@example.com"}, intent_compliant=True
    )
    print(f"✓ {call1.narrative} (intent compliant)")

    call2 = narrator.record_tool_call("send_sms", {"phone": "+1234567890"}, intent_compliant=True)
    print(f"✓ {call2.narrative} (intent compliant)")

    # Non-compliant call (drifted from intent)
    call3 = narrator.record_tool_call(
        "send_promotional_email", {"to": "user@example.com"}, intent_compliant=False
    )
    print(f"⚠ {call3.narrative} (INTENT DRIFT)")

    # Another non-compliant call
    call4 = narrator.record_tool_call("delete_account", {"user_id": "u123"}, intent_compliant=False)
    print(f"⚠ {call4.narrative} (INTENT DRIFT)")

    status = narrator.get_status()
    print(f"\n🎯 Intent violations: {status.intent_violations}")


def example_pause_and_resume() -> None:
    """StatusNarrator pause/resume for escalation."""
    print("\n=== Pause and Resume ===\n")

    narrator = StatusNarrator()
    narrator.set_objective("Approve high-value transaction")

    # Record some tool calls
    narrator.record_tool_call("verify_account", {})
    narrator.record_tool_call("check_fraud_score", {})

    # Pause for human approval
    print("⏸ Reporting a simulated approval wait...")
    narrator.pause("Awaiting manager approval for $10,000 transaction")

    status = narrator.get_status()
    print(f"Status: {'PAUSED' if status.is_paused else 'ACTIVE'}")
    print(f"Reason: {status.pause_reason}")

    # Simulate approval
    print("\n✓ Simulated manager approval; updating narrator state...")
    narrator.resume()

    # Continue with remaining calls
    narrator.record_tool_call("process_transaction", {})
    narrator.record_tool_call("send_confirmation", {})

    status = narrator.get_status()
    print(f"Status: {'PAUSED' if status.is_paused else 'ACTIVE'}")
    print(f"Total recorded calls: {status.steps_completed}")


def example_complete_workflow() -> None:
    """Complete workflow: objective → tool calls → decisions → status."""
    print("\n=== Complete Workflow ===\n")

    narrator = StatusNarrator()

    # 1. Set objective
    narrator.set_objective("Process customer order #12345")
    print("📋 Objective: Process customer order #12345\n")

    # 2. Record simulated tool calls with supplied decisions
    steps = [
        ("lookup_order", {}, Decision(status="ALLOW", risk="LOW", reason="ok")),
        ("verify_payment", {}, Decision(status="ALLOW", risk="LOW", reason="ok")),
        ("check_inventory", {}, Decision(status="WARN", risk="MEDIUM", reason="low stock")),
        ("reserve_items", {}, Decision(status="ALLOW", risk="LOW", reason="ok")),
        (
            "process_shipment",
            {},
            Decision(
                status="PAUSE", risk="HIGH", reason="needs approval", escalation_required=True
            ),
        ),
    ]

    for tool, args, decision in steps:
        call = narrator.record_tool_call(tool, args, decision=decision)
        status_char = (
            "✓" if decision.status == "ALLOW" else "⚠" if decision.status == "WARN" else "⏸"
        )
        print(f"{status_char} {call.narrative} ({decision.status})")

    # 3. Get final status
    print("\n--- Final Status ---")
    status = narrator.get_status(
        current_budget_remaining=156.75,
        current_tokens_remaining=2100,
    )

    print(f"Tool calls made: {status.tool_calls_made}")
    print(f"Decisions blocked: {status.decisions_blocked}")
    print(f"Decisions paused: {status.decisions_paused}")
    print(f"Budget remaining: ${status.current_budget_remaining:.2f}")
    print(f"Tokens remaining: {status.current_tokens_remaining}")

    # 4. Full narrative
    print("\n--- Full Narrative ---")
    print(narrator.get_narrative())


if __name__ == "__main__":
    example_basic_narration()
    example_with_decisions()
    example_with_budget_tracking()
    example_intent_compliance()
    example_pause_and_resume()
    example_complete_workflow()

    print("\n" + "=" * 50)
    print("StatusNarrator examples completed (0.6.1 API).")
    print("=" * 50)
