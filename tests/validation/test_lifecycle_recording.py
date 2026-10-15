"""Validate the committed real-HTTP lifecycle recording as native audit evidence."""

import json
from pathlib import Path

from agentic_sidecar import EventJournal


def test_recorded_approval_rejection_and_actual_effects(tmp_path):
    recorded = json.loads(Path(__file__).with_name("v0_7_lifecycle.json").read_text())
    path = tmp_path / "recording.jsonl"
    path.write_text("".join(json.dumps(row) + "\n" for row in recorded["events"]))
    assert EventJournal(recorded["task_id"], path).export() == recorded["events"]
    assert recorded["effects"] == [120]
    assert recorded["status"]["executed"] == recorded["status"]["completed"] == 1
    actions = [
        event["payload"]["action"] for event in recorded["events"] if event["kind"] == "approval"
    ]
    assert actions == ["approve_once", "reject"]
    decisions = [
        event["payload"]["decision"] for event in recorded["events"] if event["kind"] == "decision"
    ]
    assert [decision["status"] for decision in decisions] == ["PAUSE", "ALLOW", "PAUSE", "BLOCK"]
    assert decisions[1]["causal_link"] == decisions[0]["decision_id"]
    assert decisions[3]["causal_link"] == decisions[2]["decision_id"]
