# Agentic Sidecar Documentation

**Agentic Sidecar** is a companion intelligence and real-time decision supervision layer for autonomous AI agents. It attaches to your agent harness and evaluates every proposed tool call against policy, risk, intent, and budget limits *before* execution — without taking over the agent loop.

---

## Package Information

| Field | Value |
|---|---|
| **Package** | `agentic-sidecar` |
| **Version** | `0.6.0` |
| **Maturity** | Pre-Alpha |
| **License** | MIT |
| **Python** | ≥ 3.10 |
| **PyPI** | [pypi.org/project/agentic-sidecar](https://pypi.org/project/agentic-sidecar/) |
| **GitHub** | [DeepAgentLabs/agentic-sidecar](https://github.com/DeepAgentLabs/agentic-sidecar) |

---

## What it does

Agentic Sidecar evaluates agent decisions before they execute. Instead of hoping your agent behaves correctly, it provides a structured Decision Gate that:

1. **Checks policy** — YAML-driven allow/deny rules matched against tool names
2. **Classifies risk** — LOW / MEDIUM / HIGH based on argument patterns
3. **Validates intent** — ensures tool arguments stay within user-declared constraints
4. **Enforces budget** — halts execution if cost or token ceilings are reached
5. **Evaluates plans** — checks multi-step plans for unnecessary steps or overreach
6. **Challenges decisions** — LLM-based critic and judge evaluators (opt-in)

All of this runs in either **Observe mode** (log decisions, never block) or **Govern mode** (BLOCK decisions raise `SidecarBlockedError` and stop execution).

---

## Quick navigation

| Page | What it covers |
|---|---|
| [Getting started](getting-started.md) | Install, minimal setup, first governed agent |
| [Architecture](architecture.md) | Core design, Decision Gate pipeline, module boundaries |
| [Features](features.md) | All implemented capabilities with status labels |
| [Configuration](configuration.md) | `Sidecar` constructor, YAML policy/risk files, all options |
| [API reference](api-reference.md) | Full Python API — classes, methods, types |
| [CLI reference](cli-reference.md) | `agentic-sidecar status`, `version`, `demo` commands |
| [Integrations](integrations.md) | LangGraph, CrewAI, AutoGen, OpenAI Agents, Google ADK |
| [Examples](examples.md) | Runnable example scripts from `examples/` |
| [Troubleshooting](troubleshooting.md) | Common errors and how to fix them |
| [Limitations](limitations.md) | Known constraints and current boundaries |
| [Roadmap](roadmap.md) | Planned capabilities — not yet implemented |
