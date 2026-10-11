"""Framework adapters -- the decision-boundary interception point for each
supported agent framework, routing proposed actions through
`Sidecar.evaluate()`.

`langgraph.py` is implemented as of v0.1 and is the only adapter that should
exist until it's proven stable -- do not start a second adapter yet, the
interception abstraction needs to survive contact with one real framework
first (ROADMAP.md's Design Constraint 1). The other four
(`crewai`, `autogen`, `openai_agents`, `google_adk`) are placeholders for
v0.8.

No module in this package is imported here automatically: each adapter is a
separate optional surface (see `pyproject.toml`'s `langgraph` extra), and
importing `agentic_sidecar.adapters` should never require every framework's
SDK to be installed.
"""
