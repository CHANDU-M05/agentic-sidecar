"""Versioned native correlation convention; not a stable AIOS schema."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from agentic_sidecar.core.decision import Decision
from agentic_sidecar.core.sidecar import Sidecar
from agentic_sidecar.operations.events import verify_events


class Correlation(BaseModel):
    """Host-supplied IDs of the exact trace span being supervised."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    run_id: str = Field(min_length=1)
    trace_id: str = Field(min_length=1)
    span_id: str = Field(min_length=1)


class CorrelatedDecision(Decision):
    """Serialized evidence requires the producer's original decision identity."""

    decision_id: str = Field(min_length=1)


class DecisionEvidence(BaseModel):
    """Authorized projection; reasons/trigger details may contain sensitive arguments."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    contract_version: Literal["sidecar.correlation/1"] = "sidecar.correlation/1"
    correlation: Correlation
    task_id: str = Field(min_length=1)
    system_id: str | None = None
    agent_id: str | None = None
    source_event_id: str = Field(min_length=1)
    timestamp: datetime
    policy_version: str = Field(min_length=1)
    tool_name: str
    boundary: str
    decision: CorrelatedDecision

    @field_validator("timestamp")
    @classmethod
    def aware_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Evidence timestamps must be timezone-aware")
        return value


def export_decisions(sidecar: Sidecar, correlation: Correlation) -> list[DecisionEvidence]:
    """Verify the native journal, then project decisions with explicit host IDs.

    Call at a scoped boundary/session: these IDs apply to all exported decisions.
    Reasons may contain sensitive data; export only to authorized readers. The
    projection is not an independently verifiable copy of the original journal.
    """
    events = sidecar.runtime.journal.export()
    verify_events(events, task_id=sidecar.runtime.task_id)
    records = []
    for event in events:
        if event["kind"] != "decision":
            continue
        payload = event["payload"]
        scope = payload["context"]["metadata"].get("sidecar.scope", {})
        records.append(
            DecisionEvidence(
                correlation=correlation,
                task_id=scope.get("task_id", event["task_id"]),
                system_id=scope.get("system_id"),
                agent_id=scope.get("agent_id"),
                source_event_id=event["event_id"],
                timestamp=event["timestamp"],
                policy_version=payload["policy_version"],
                tool_name=payload["trigger"]["tool_name"],
                boundary=payload["trigger"]["boundary_type"],
                decision=payload["decision"],
            )
        )
    return records
