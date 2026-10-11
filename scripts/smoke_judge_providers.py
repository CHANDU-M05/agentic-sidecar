"""Opt-in live provider smoke test; no credentials are printed or written."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone

from agentic_sidecar import AnthropicJudge, JudgeEvaluator, OpenAIJudge

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--provider", choices=["openai", "anthropic", "all"], default="all")
parser.add_argument("--model", help="Explicit model; use with a single provider")
args = parser.parse_args()
if args.model and args.provider == "all":
    parser.error("--model requires a single --provider")
results = []
for name, cls, key, model_key in [
    ("openai", OpenAIJudge, "OPENAI_API_KEY", "SIDECAR_OPENAI_MODEL"),
    ("anthropic", AnthropicJudge, "ANTHROPIC_API_KEY", "SIDECAR_ANTHROPIC_MODEL"),
]:
    if args.provider not in (name, "all"):
        continue
    model = args.model or os.environ.get(model_key)
    row = {"provider": name, "timestamp": datetime.now(timezone.utc).isoformat()}
    if not os.environ.get(key) or not model:
        row.update(status="not_run", reason="Requires API credentials and an explicit model")
    else:
        try:
            judge = JudgeEvaluator(cls(model, timeout_ms=20000), cost_limit=None, timeout_ms=20000)
            result = judge.evaluate(
                {
                    "tool_name": "read_order",
                    "arguments": {"id": "fixture"},
                    "goal": "Read an order",
                    "constraints": {},
                    "history": [],
                    "plan": [],
                }
            )
            row.update(
                status="passed",
                model=model,
                decision=result.status,
                usage=result.metadata["usage"],
                latency_ms=result.latency_ms,
            )
        except Exception as exc:
            row.update(status="failed", error_type=type(exc).__name__)
    results.append(row)
print(json.dumps(results, indent=2))
if any(result["status"] == "failed" for result in results):
    raise SystemExit(1)
