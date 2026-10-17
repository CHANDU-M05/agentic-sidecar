"""Credential-free versioned decision export; sibling installation is optional."""

from agentic_sidecar import DecisionContext, Sidecar
from agentic_sidecar.integrations.correlation import Correlation, export_decisions


def main() -> None:
    sidecar = Sidecar(on_sidecar_failure="fail_closed", mode="govern")
    sidecar.evaluate(DecisionContext(tool_name="read_order", tool_args={"order": "A100"}))
    records = export_decisions(
        sidecar, Correlation(run_id="run-1", trace_id="trace-1", span_id="span-1")
    )
    assert records[0].decision.status == "ALLOW"
    print(records[0].model_dump_json(indent=2))


if __name__ == "__main__":
    main()
