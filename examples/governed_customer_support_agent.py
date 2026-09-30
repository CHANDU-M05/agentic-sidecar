"""Governed Customer Support Agent — Practical Sidecar Governance Use Case.

Demonstrates how Agentic Sidecar adds policy enforcement, risk controls,
intent constraints, budget ceilings, and decision provenance to an AI-agent
workflow.

Run:
    python examples/governed_customer_support_agent.py
"""

from __future__ import annotations

import logging
from typing import Any

from agentic_sidecar import Sidecar, SidecarBlockedError
from agentic_sidecar.adapters.langgraph import attach
from agentic_sidecar.gate import BudgetGuardian
from agentic_sidecar.gate.policy import PolicyAdvisor, PolicyRule
from agentic_sidecar.gate.risk import RiskEvaluator, RiskRule
from agentic_sidecar.intent import ConstraintBinding, IntentEnvelope, IntentGuardian, Requester

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")


# 1. Define Agent Tools
def read_order(order_id: str) -> dict[str, Any]:
    """Retrieve order details by order ID."""
    print(f"  [EXEC] Executing read_order('{order_id}')...")
    return {
        "order_id": order_id,
        "customer_id": "cust_1001",
        "amount": 450.0,
        "status": "delivered",
    }


def issue_refund(order_id: str, amount: float, reason: str = "customer dispute") -> dict[str, Any]:
    """Issue a monetary refund to customer."""
    print(f"  [EXEC] Executing issue_refund('{order_id}', amount=${amount})...")
    return {
        "status": "refund_processed",
        "order_id": order_id,
        "refund_amount": amount,
        "reason": reason,
    }


def delete_customer_record(customer_id: str) -> dict[str, Any]:
    """Permanently delete a customer record from database."""
    print(f"  [EXEC] Executing delete_customer_record('{customer_id}')...")
    return {"status": "deleted", "customer_id": customer_id}


def run_use_case_demo() -> None:
    print("=" * 80)
    print("      GOVERNED CUSTOMER SUPPORT AGENT — SIDECAR USE CASE DEMO")
    print("=" * 80)

    # 2. Configure Sidecar Components
    # Policy Advisor: hard deny on account deletions
    policy = PolicyAdvisor(
        rules=[
            PolicyRule(
                tool="delete_*",
                effect="deny",
                reason="Account deletion requires explicit admin authorization",
            )
        ]
    )

    # Risk Evaluator: HIGH risk on refunds > $500
    risk = RiskEvaluator(
        rules=[
            RiskRule(
                tool="issue_refund",
                arg_name="amount",
                arg_op="gt",
                arg_value=500.0,
                risk="HIGH",
                reason="Refund exceeds standard support representative threshold ($500)",
            )
        ]
    )

    # Intent Envelope & Guardian: user asked to inspect & process refund <= $500
    envelope = IntentEnvelope(
        goal="Assist customer with order dispute and refund up to $500",
        requested_by=Requester(type="human", id="support_lead_42"),
        constraints={"maximum_refund": 500.0},
    )

    intent_bindings = [
        ConstraintBinding(
            constraint="maximum_refund",
            tool="issue_refund",
            arg_name="amount",
            op="lte",
            severity="BLOCK",
            reason="Refund amount exceeds user-authorized limit ($500)",
        )
    ]
    guardian = IntentGuardian(envelope, intent_bindings)

    # Budget Guardian: $5.00 budget ceiling
    budget = BudgetGuardian(max_cost=5.00)

    # 3. Create Sidecar Runtime in Observe Mode
    print("\n--- PHASE 1: OBSERVE MODE (Monitoring & Logging Only) ---")
    sidecar_observe = Sidecar(
        on_sidecar_failure="fail_closed",
        mode="observe",
        roles=["policy", "risk", "intent_guardian", "budget"],
        policy=policy,
        risk=risk,
        intent=guardian,
        budget=budget,
        risk_block_threshold="HIGH",
    )

    wrapped_tools_observe = attach(
        sidecar_observe, [read_order, issue_refund, delete_customer_record]
    )
    obs_read, obs_refund, obs_delete = wrapped_tools_observe

    print("\n1.1 Agent calls read_order('ORD-999'):")
    obs_read("ORD-999")

    print("\n1.2 Agent calls issue_refund('ORD-999', amount=250.0):")
    obs_refund("ORD-999", 250.0)

    print("\n1.3 Agent calls issue_refund('ORD-999', amount=850.0) [Exceeds Limit]:")
    obs_refund("ORD-999", 850.0)  # In observe mode, executes anyway but logs BLOCK

    print("\n1.4 Agent calls delete_customer_record('cust_1001') [Policy Violation]:")
    obs_delete("cust_1001")  # In observe mode, executes anyway but logs BLOCK

    print("\nSidecar Decisions Recorded in Observe Mode:")
    for ctx, dec in sidecar_observe.decisions:
        symbol = "✓" if dec.status == "ALLOW" else "🚫"
        print(f"  {symbol} {dec.status:<6} | Tool: {ctx.tool_name:<22} | Reason: {dec.reason}")

    # 4. Create Sidecar Runtime in Govern Mode
    print("\n" + "=" * 80)
    print("--- PHASE 2: GOVERN MODE (Active Policy & Intent Enforcement) ---")
    print("=" * 80)

    sidecar_govern = Sidecar(
        on_sidecar_failure="fail_closed",
        mode="govern",
        roles=["policy", "risk", "intent_guardian", "budget"],
        policy=policy,
        risk=risk,
        intent=guardian,
        budget=BudgetGuardian(max_cost=5.00),
        risk_block_threshold="HIGH",
    )

    wrapped_tools_govern = attach(
        sidecar_govern, [read_order, issue_refund, delete_customer_record]
    )
    gov_read, gov_refund, gov_delete = wrapped_tools_govern

    print("\n2.1 Agent calls read_order('ORD-999'):")
    res1 = gov_read("ORD-999")
    print(f"  -> Result: {res1}")

    print("\n2.2 Agent calls issue_refund('ORD-999', amount=300.0) [Within Limit]:")
    res2 = gov_refund("ORD-999", 300.0)
    print(f"  -> Result: {res2}")

    print("\n2.3 Agent calls issue_refund('ORD-999', amount=850.0) [Intent Violation]:")
    try:
        gov_refund("ORD-999", 850.0)
    except SidecarBlockedError as exc:
        print(f"  🛑 BLOCKED BY SIDECAR: {exc}")

    print("\n2.4 Agent calls delete_customer_record('cust_1001') [Policy Violation]:")
    try:
        gov_delete("cust_1001")
    except SidecarBlockedError as exc:
        print(f"  🛑 BLOCKED BY SIDECAR: {exc}")

    print("\nSidecar Audit Summary:")
    print(f"Total Interceptions: {len(sidecar_govern.decisions)}")
    blocked_count = sum(1 for _, d in sidecar_govern.decisions if d.status == "BLOCK")
    allowed_count = sum(1 for _, d in sidecar_govern.decisions if d.status == "ALLOW")
    print(f"  Allowed Actions: {allowed_count}")
    print(f"  Blocked Actions: {blocked_count}")
    print("=" * 80)


if __name__ == "__main__":
    run_use_case_demo()
