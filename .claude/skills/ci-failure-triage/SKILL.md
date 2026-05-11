---
name: ci-failure-triage
description: Use when CI fails on a PR or main. Walks through reproducing locally and root-causing without bypassing checks.
---

# CI failure triage

## Classify the failure

Look at the GitHub Actions log and decide which stage failed:

- **Format check** (`make format-check`) — ruff disagrees with the committed formatting.
- **Lint** (`make lint-ci`) — ruff lint rule.
- **Typecheck** (`make typecheck-fast`) — mypy.
- **Tests** (`make test-fast`) — failing or erroring test.
- **Coverage** — gate fell below 90%.
- **Docker** — compose render or build failed.
- **CodeQL / dependency review** — security workflows.

## Reproduce locally

Run the same Make target that failed in CI:

- `make format-check`
- `make lint-ci`
- `make typecheck-fast`
- `make test-fast`
- `make test-cov`
- `make docker-prod-config`

## Fix at root cause

- Do not add `# type: ignore` or `# noqa` to silence a check unless the
  underlying behavior is genuinely correct and the tool is wrong.
- Do not use `git commit --no-verify` to bypass pre-commit.
- For flaky tests, rerun once to confirm flakiness, then mark with the
  `slow` marker and open a follow-up issue rather than disabling the test.

## Confirm fix

Run `make ci-local` locally. Push. Watch the workflow re-run.
