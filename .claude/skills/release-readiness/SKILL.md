---
name: release-readiness
description: Use when preparing a versioned release of gtex-link. Walks through changelog, version bump, tag, and watching the release workflow.
---

# Release readiness

## Pre-flight

1. Confirm `main` is green: latest CI run succeeded.
2. Verify there are no outstanding `dependabot` PRs that should land first.
3. Confirm `CHANGELOG.md` has an Unreleased section with all user-visible changes since the last tag.

## Bump

1. Open `pyproject.toml` and bump `version`. Follow semver:
   - `MAJOR.MINOR.PATCH`
   - MAJOR for breaking changes
   - MINOR for feature additions
   - PATCH for fixes
2. Rewrite the `[Unreleased]` heading in `CHANGELOG.md` to `[X.Y.Z] - YYYY-MM-DD` and add a fresh empty `[Unreleased]` section above it.
3. Commit: `chore(release): bump to X.Y.Z`.

## Tag and push

```bash
git tag vX.Y.Z
git push origin main vX.Y.Z
```

## Watch

The `release.yml` workflow runs on `v*` tag pushes. It runs `make ci-local`, validates compose configs, and builds the release Docker image.

## Roll forward

If `release.yml` fails, fix on `main`, bump to `vX.Y.(Z+1)`, retag.
