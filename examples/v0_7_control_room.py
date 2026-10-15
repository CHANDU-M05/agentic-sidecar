"""Real paused refund, HTTP approval/rejection and immutable causal evidence.

Run offline for automatic approval/rejection. --interactive waits for the
Control Room operator (SIDECAR_OPERATOR_TOKEN required). --record writes JSON
acceptance evidence; --audit writes durable JSONL to a new file.
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from agentic_sidecar import (
    BudgetGuardian,
    EventJournal,
    OperatorServer,
    Sidecar,
    SidecarBlockedError,
    TaskRuntime,
)
from agentic_sidecar.adapters.langgraph import attach
from agentic_sidecar.intent.alignment import IntentGuardian
from agentic_sidecar.intent.envelope import IntentEnvelope
from agentic_sidecar.operations.client import request
from agentic_sidecar.status.live import narrate_status


def run(*, interactive: bool = False, audit: Path | None = None) -> dict:
    token = os.environ.get("SIDECAR_OPERATOR_TOKEN") or secrets.token_urlsafe(32)
    if interactive and not os.environ.get("SIDECAR_OPERATOR_TOKEN"):
        raise ValueError("Set SIDECAR_OPERATOR_TOKEN to a secret of at least 32 characters")
    journal = EventJournal("refund-demo", audit)
    runtime = TaskRuntime(journal=journal, approval_timeout=300 if interactive else 10)
    sidecar = Sidecar(
        on_sidecar_failure="fail_closed",
        mode="govern",
        runtime=runtime,
        escalation_handler=runtime,
        roles=["intent_guardian", "budget"],
        intent=IntentGuardian(
            IntentEnvelope(goal="Review a customer refund", requested_by={"id": "customer"})
        ),
        budget=BudgetGuardian(max_cost=1, current_cost=1),
    )
    effects = []

    def refund(amount: int) -> str:
        """Issue the locally simulated refund only after actual approval."""
        effects.append(amount)
        return f"Refunded {amount}"

    wrapped = attach(sidecar, [refund])[0]
    with (
        OperatorServer(runtime, token=token, actor="demo-operator") as server,
        ThreadPoolExecutor() as pool,
    ):
        print(f"Control Room: {server.url}")
        for action in [None] if interactive else ["approve_once", "reject"]:
            future = pool.submit(wrapped, 120)
            deadline = time.monotonic() + 5
            pending = []
            while not pending and time.monotonic() < deadline:
                pending = request(server.url, token, "/status")["pending"]
                if not pending:
                    time.sleep(0.01)
            if not pending:
                raise RuntimeError("No paused action appeared")
            print("Paused: no additional refund has executed.")
            if action is not None:
                request(
                    server.url,
                    token,
                    "/approval",
                    {
                        "decision_id": pending[0]["decision_id"],
                        "action": action,
                    },
                )
            try:
                print(future.result(timeout=305 if interactive else 15))
            except SidecarBlockedError:
                print("Rejected: tool did not execute.")
        snapshot = request(server.url, token, "/status")
        events = request(server.url, token, "/events")
        print(narrate_status(snapshot))
    return {"task_id": runtime.task_id, "effects": effects, "status": snapshot, "events": events}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interactive", action="store_true")
    parser.add_argument("--record", type=Path)
    parser.add_argument("--audit", type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as directory:
        result = run(
            interactive=args.interactive, audit=args.audit or Path(directory) / "audit.jsonl"
        )
    if args.record:
        args.record.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
