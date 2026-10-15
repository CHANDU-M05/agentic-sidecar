# Contributing

Thanks for helping make `agentic-sidecar` better for everyone building
governable autonomous AI agents.

The checkout targets 0.6.1 governance/evaluator enhancements. See
[ROADMAP.md](ROADMAP.md) for implemented scope, remaining acceptance evidence
and upcoming work before starting on a module.

## Local setup

```bash
git clone https://github.com/DeepAgentLabs/agentic-sidecar.git
cd agentic-sidecar
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev,docs,langgraph]"
```

Or with `uv`:

```bash
uv sync --locked --extra dev --extra docs --extra langgraph
```

## Development workflow

1. Check [ROADMAP.md](ROADMAP.md) for the current build order — modules
   have a stated planned version for a reason (see its Design Constraints
   section). Keep changes within the intended milestone.
2. Create a focused branch from `main`.
3. Add or update tests with every behavior change.
4. Add or update user-facing examples when the feature or expected workflow
   changes.
5. If a roadmap item is completed or its status changes, update
   `README.md` and `ROADMAP.md` in the same pull request.
6. If the work is release-ready, update `pyproject.toml`,
   `src/agentic_sidecar/__init__.py`, and `CHANGELOG.md` as part of the
   release.
7. Run:

```bash
make check
make docs-check
make examples-check
make release-check
```

8. Keep PRs focused — one concern per pull request.
9. Write clear commit messages describing *why*, not just *what*.

## Turning a placeholder module into a real one

1. Read the module's docstring in `src/agentic_sidecar/` — it states what
   the module is for and which ROADMAP version it belongs to.
2. Implement against the Python API sketched in `README.md`'s
   [Planned Python API](README.md#planned-python-api) section, adjusting
   the README if the real shape needs to differ.
3. Respect the Package Boundaries in [AGENTS.md](AGENTS.md) (e.g. `gate/`
   must not depend on `evaluators/`).
4. Add tests in `tests/`.
5. Add or update a usage example.
6. Update README, ROADMAP, and CHANGELOG in the same PR.

## Releases

Releases are automated via GitHub Actions when a version tag is pushed.

### Release checklist

1. Update the version string in all three locations:
   - `pyproject.toml` → `version = "X.Y.Z"`
   - `src/agentic_sidecar/__init__.py` → `__version__ = "X.Y.Z"`
   - `CHANGELOG.md` → add a `## [X.Y.Z] - YYYY-MM-DD` section
2. Commit the release preparation on a feature branch and merge through review.
3. On main, create an annotated vX.Y.Z tag on the merge commit using the matching
   changelog section as its message (`--cleanup=verbatim` preserves Markdown).
4. Push that release tag to trigger publication.

The release workflow validates tag, source versions, changelog, behavior, docs,
and distribution metadata before publishing via PyPI Trusted Publishing. It
then creates the GitHub release using the same changelog section. See
[AGENTS.md](AGENTS.md) for the two-phase release procedure.
