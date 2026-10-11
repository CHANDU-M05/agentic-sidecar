"""Four deterministic scenarios; measurements cover bound fields, not semantic authority."""

import json
from pathlib import Path

import pytest

from agentic_sidecar import Sidecar, SidecarBlockedError
from agentic_sidecar.adapters.langgraph import attach
from agentic_sidecar.intent import ConstraintBinding, IntentEnvelope, IntentGuardian

SCENARIOS = json.loads(Path(__file__).with_name("intent_scenarios.json").read_text())


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda scenario: scenario["name"])
@pytest.mark.parametrize("enabled", [False, True])
@pytest.mark.parametrize("unsafe", [False, True])
def test_intent_guardian_on_off_clean_controls(scenario, enabled, unsafe):
    executed = []

    def action(**kwargs):
        executed.append(kwargs)
        return "executed"

    action.__name__ = scenario["tool"]
    guardian = IntentGuardian(
        IntentEnvelope(
            goal=scenario["goal"],
            requested_by={"id": "u"},
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
    sidecar = Sidecar(
        on_sidecar_failure="fail_closed",
        mode="govern",
        roles=["intent_guardian"] if enabled else [],
        intent=guardian if enabled else None,
    )
    # Use an explicit signature to preserve the bound argument at interception.
    import inspect

    action.__signature__ = inspect.Signature(
        [inspect.Parameter(scenario["argument"], inspect.Parameter.KEYWORD_ONLY)]
    )
    wrapped = attach(sidecar, [action])[0]
    arguments = {scenario["argument"]: scenario["unsafe" if unsafe else "clean"]}
    if enabled and unsafe:
        with pytest.raises(SidecarBlockedError):
            wrapped(**arguments)
        assert executed == []
    else:
        assert wrapped(**arguments) == "executed"
        assert executed == [arguments]
