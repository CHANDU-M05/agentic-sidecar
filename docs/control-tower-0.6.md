# Control Tower 0.6.0 compatibility

Tower combines Phase 6 (local MCP connector and investigation) and Phase 6A
(approved staging incident-to-recovery) in a single **0.6.0** release, paired with
MCP **0.3.6**. Sibling packages remain optional; no producer dependency floor or
runtime behavior changes in this documentation alignment.

Sidecar 0.8.0 retains decision-time supervision, dispatch blocking and task
stop/restart ownership. Tower provides a thin optional SidecarContainmentAdapter.
Install an mcp revoker in TaskRuntime to coordinate native MCP key revocation.
Stop does not depend on model approval; explicit human restart still uses
Sidecar stopped/idle/revocation checks. In-flight calls and unsupported downstream
credentials prevent claims of universal containment.

The first supported remediation target is Tower's deterministic local SQLite
staging dependency runtime. Exact-preview approval binds target, dependency,
impact, rollback and recovery criteria. Tower commits a consumed execution claim
before dispatch; duplicates and interrupted actions cannot automatically replay.
A successful command only awaits verification: fresh Lens success, a correlated
passing Evals gate and an independent successful probe determine resolution.
Failed recovery escalates. Production runtime adapters, hosted MCP tenant
credential binding, bulk operations and incident console views remain planned.

## Example and dependency matrix

From a sibling workspace, create a versioned Tower checkout (omit clone if
already present). The example first ships in `v0.6.0`; it is absent from 0.5.x:

```bash
git clone --branch v0.6.0 https://github.com/DeepAgentLabs/agenticops-control-tower.git ../tower-0.6.0
cd ../tower-0.6.0
uv run --with ../agenticlens --with ../agentic-evals python examples/incident_recovery.py
uv run --with ../agenticlens --with ../agentic-evals python examples/incident_recovery.py --fail-verification
make test-ecosystem
```

The two walkthrough outputs are `resolved` and `escalated`. The actual producer
matrix is Lens 0.7.1, Evals 0.7.1, Sidecar 0.8.0 and Chaos 0.5.3; MCP 0.3.6
exposes the real authenticated Tower 0.6.0 API. Native artifact readers do not
require those packages at Tower startup. MCP uses HTTP and does not import Tower.
`ai-operations-spec` 0.5.1 is a repository/catalog release, not an AIOS
schema version. Lens supports AIOS v0.4-draft only; Tower-local incident
contracts make no AIOS conformance claim.

See [the operator guide](https://github.com/DeepAgentLabs/agenticops-control-tower/blob/v0.6.0/docs/incident-recovery.md)
and [MCP setup](https://github.com/DeepAgentLabs/agenticops-control-tower/blob/v0.6.0/docs/mcp-connector.md)
for API requests, credentials, supported scope and recovery limits.
