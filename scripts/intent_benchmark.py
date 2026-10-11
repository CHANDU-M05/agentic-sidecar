"""Reproduce the narrow deterministic Intent Guardian fixture measurements."""

from __future__ import annotations

import json
from pathlib import Path

from agentic_sidecar import DecisionContext, Sidecar
from agentic_sidecar.intent import ConstraintBinding, IntentEnvelope, IntentGuardian

root = Path(__file__).resolve().parents[1]
scenarios = json.loads((root / "tests/validation/intent_scenarios.json").read_text())
rows = []
for scenario in scenarios:
    guardian = IntentGuardian(
        IntentEnvelope(
            goal=scenario["goal"],
            requested_by={"id": "fixture"},
            constraints={scenario["constraint"]: scenario["limit"]},
        ),
        [
            ConstraintBinding(
                constraint=scenario["constraint"],
                tool=scenario["tool"],
                arg_name=scenario["argument"],
                op=scenario["operator"],
            )
        ],
    )
    row = {"scenario": scenario["name"]}
    for enabled in (False, True):
        sidecar = Sidecar(
            on_sidecar_failure="fail_closed",
            mode="govern",
            roles=["intent_guardian"] if enabled else [],
            intent=guardian if enabled else None,
        )
        for sample in ("unsafe", "clean"):
            decision = sidecar.evaluate(
                DecisionContext(
                    tool_name=scenario["tool"], tool_args={scenario["argument"]: scenario[sample]}
                )
            )
            row[f"guardian_{'on' if enabled else 'off'}_{sample}"] = decision.status
    rows.append(row)
print(
    json.dumps(
        {
            "scope": "Four deterministic bound-field fixtures; no live model or authority claims",
            "unsafe_cases": len(rows),
            "clean_controls": len(rows),
            "guardian_on_catch_rate": sum(row["guardian_on_unsafe"] == "BLOCK" for row in rows)
            / len(rows),
            "guardian_on_false_positive_rate": sum(
                row["guardian_on_clean"] != "ALLOW" for row in rows
            )
            / len(rows),
            "guardian_off_catch_rate": sum(row["guardian_off_unsafe"] == "BLOCK" for row in rows)
            / len(rows),
            "results": rows,
        },
        indent=2,
    )
)
