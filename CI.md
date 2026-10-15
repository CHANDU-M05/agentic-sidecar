# CI Readiness — Pre-push Checklist

Run these checks locally before every push or PR.

## Docs-only shortcut

For documentation changes, run strict docs/snippet/link checks:

```bash
make docs-check
```

## Required checks (all code changes)

```bash
make check
```

This runs lint → format-check → typecheck → test in sequence. If any step
fails, fix it before pushing.

Or run steps individually:

1. **Clean tree** — no accidental untracked files, no `.env` or secrets

   ```bash
   git status --short
   ```

2. **Lint**

   ```bash
   make lint
   ```

3. **Format**

   ```bash
   make format-check
   ```

   If it fails: `make format && make format-check`

4. **Type check**

   ```bash
   make typecheck
   ```

5. **Test**

   ```bash
   make test
   ```

## When to run full coverage

Run `make test-cov` instead of `make test` for any change to `core/`,
`gate/`, or `intent/` — those hold the Decision Gate logic every other
module depends on.

## CI parity

The CI workflow checks Python 3.10–3.13 with the LangGraph extra, including
real governed ToolNode dispatch, offline examples, Python documentation fences,
local file links and release source metadata. A package job checks wheel/sdist.
The docs workflow builds strictly on PRs and deploys Pages only from main.

Release automation validates tag/source/changelog first, runs runtime/example/docs
checks, validates built distribution metadata, then publishes via OIDC. Manual
release dispatch requires a tag ref. Live provider smoke tests are opt-in with
credentials; deterministic SDK contracts run without credentials in normal CI.

```bash
make check
make docs-check
make examples-check
make release-check
```

Add sibling integration jobs when the corresponding integration has real code.
