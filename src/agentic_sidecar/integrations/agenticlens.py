"""Explicit, optional decision export to a correlated AgenticLens Run."""

from importlib import import_module
from typing import Any

from agentic_sidecar.core.sidecar import Sidecar
from agentic_sidecar.integrations.correlation import Correlation, export_decisions


def attach_decisions(sidecar: Sidecar, run: Any, *, span_id: str) -> None:
    """Attach verified decision projections; Lens owns trace/timeline behavior."""
    reader = import_module("agenticlens.integrations.sidecar")
    reader.verify_journal(sidecar.runtime.journal.export(), task_id=sidecar.runtime.task_id)
    correlation = Correlation(run_id=run.run_id, trace_id=run.trace_id, span_id=span_id)
    reader.attach_decisions(
        run, [record.model_dump(mode="json") for record in export_decisions(sidecar, correlation)]
    )
