"""Optional sibling readback: native supervision evidence never changes health."""

from datetime import datetime, timezone

import pytest

from agentic_sidecar import Decision, DecisionContext, Sidecar, __version__

pytest.importorskip("agenticops_control_tower")
from agenticops_control_tower.models import AgentRegistrationPayload
from agenticops_control_tower.models.evidence import EvidenceLink
from agenticops_control_tower.snapshot import create_api


@pytest.mark.parametrize(
    "status", ["ALLOW", "WARN", "BLOCK", "CHALLENGE", "REPLAN", "PAUSE", "ESCALATE"]
)
def test_native_runtime_evidence_preserves_outcome_and_deployment_health(status):
    sidecar = Sidecar(on_sidecar_failure="fail_closed", mode="govern")
    sidecar.before_tool_call(lambda context: Decision(status=status, risk="HIGH", reason="Fixture"))
    decision = sidecar.evaluate(DecisionContext(tool_name="read"))
    artifact = sidecar.runtime.journal.export()[-1]["payload"]["decision"]
    api = create_api()
    api.register_agent(
        AgentRegistrationPayload(
            agent_id="deployment",
            name="Fixture",
            environment="test",
            runtime="custom",
            framework="custom",
            status="healthy",
        )
    )
    link = EvidenceLink(
        agent_id="deployment",
        source="agentic-sidecar",
        source_version=__version__,
        artifact_type="decision",
        artifact_ref="decision:" + decision.decision_id,
        observed_at=datetime.now(timezone.utc),
    )
    summary = api.summarize_evidence(link, artifact)
    assert summary.availability == "available"
    assert summary.details["status"] == status
    assert summary.details["risk"] == "HIGH"
    assert api.get_status().healthy_agents == 1
    assert api.get_agent("deployment").heartbeat_count == 0
