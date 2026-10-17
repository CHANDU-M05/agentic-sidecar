"""Native correlation, journal verification and optional sibling consumers."""

from copy import deepcopy

import pytest

from agentic_sidecar import DecisionContext, Sidecar, SidecarBlockedError
from agentic_sidecar.integrations.agentic_chaos import evaluate_recovery
from agentic_sidecar.integrations.correlation import Correlation, export_decisions
from agentic_sidecar.operations.events import verify_events


def test_verified_export_and_tamper_rejection() -> None:
    sidecar = Sidecar(on_sidecar_failure="fail_closed")
    sidecar.evaluate(DecisionContext(tool_name="read"))
    correlation = Correlation(run_id="run", trace_id="trace", span_id="span")
    (evidence,) = export_decisions(sidecar, correlation)
    assert evidence.decision.decision_id == sidecar.decisions[0][1].decision_id
    assert evidence.correlation == correlation
    events = deepcopy(sidecar.runtime.journal.export())
    events[-1]["payload"]["decision"]["status"] = "BLOCK"
    with pytest.raises(ValueError, match="audit"):
        verify_events(events, task_id=sidecar.runtime.task_id)


def test_real_lens_correlation_and_timeline() -> None:
    pytest.importorskip("agenticlens.integrations.sidecar")
    from agenticlens.diagnosis import diagnose_run
    from agenticlens.models.trace import Run, Span, SpanType

    from agentic_sidecar.integrations.agenticlens import attach_decisions

    run = Run(
        application_name="sidecar-integration",
        spans=[Span(name="read", span_type=SpanType.TOOL_CALL)],
    )
    sidecar = Sidecar(on_sidecar_failure="fail_closed")
    sidecar.evaluate(DecisionContext(tool_name="read"))
    attach_decisions(sidecar, run, span_id=run.spans[0].span_id)
    attach_decisions(sidecar, run, span_id=run.spans[0].span_id)
    assert len(run.spans[0].attributes["sidecar.decisions"]) == 1
    assert any(event.kind == "supervision_decision" for event in diagnose_run(run).timeline.events)


def test_real_chaos_recovery_and_failure_policy() -> None:
    pytest.importorskip("agentic_chaos")
    from agentic_chaos.models.chaos_event import ChaosEvent

    from agentic_sidecar.gate.policy import PolicyAdvisor, PolicyRule

    event = ChaosEvent(fault_type="tool_call_failure", outcome="errored", message="fixture")
    sidecar = Sidecar(
        on_sidecar_failure="fail_closed",
        mode="govern",
        policy=PolicyAdvisor([PolicyRule(tool="delete", effect="deny")]),
    )
    with pytest.raises(SidecarBlockedError):
        evaluate_recovery(sidecar, event.model_dump(mode="json"), tool_name="delete", arguments={})
    assert sidecar.decisions[0][0].metadata["chaos.event_id"] == event.id
    assert (
        evaluate_recovery(
            sidecar, event.model_dump(mode="json"), tool_name="read", arguments={}
        ).status
        == "ALLOW"
    )
