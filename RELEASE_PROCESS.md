# Release Process

This document describes the public release flow for CORTEX Persist.

## Release Model

CORTEX Persist uses tagged releases for package publication.

- version metadata lives in [pyproject.toml](pyproject.toml)
- release tags follow the `v*` pattern
- PyPI publishing is handled by GitHub Actions via two workflows:
  - [`.github/workflows/release.yml`](.github/workflows/release.yml) — authoritative release workflow (signed artifacts, Sigstore, SBOM)
  - [`.github/workflows/publish.yml`](.github/workflows/publish.yml) — streamlined PyPI publish on GitHub Release creation

## PyPI Trusted Publishing Setup

This repository uses PyPI Trusted Publishing through GitHub Actions.

The exact identity that PyPI must trust is:

- PyPI project name: `cortex-persist`
- GitHub owner: `borjamoskv`
- GitHub repository: `Cortex-Persist`
- workflow filename: `release.yml`
- GitHub Actions environment: `pypi`

For the first public release, configure a **pending publisher** on PyPI before pushing the release tag. PyPI documents that pending publishers can create a project on first use and then convert into normal publishers automatically.

For an existing PyPI project, configure a normal Trusted Publisher with the same identity tuple above.

If the repository name, workflow filename, or environment name changes, the PyPI publisher configuration must be updated to match or publishing will fail.

## Release Workflow

The authoritative workflow is:

- [.github/workflows/release.yml](.github/workflows/release.yml)

At a high level, the workflow:

1. checks out the repository
2. builds source and wheel artifacts
3. generates build provenance
4. publishes to PyPI
5. signs artifacts with Sigstore
6. uploads signed artifacts for traceability
7. verifies that the released version is visible on PyPI

## Release Preflight

The release pipeline now performs an explicit preflight before publish:

- builds wheel and sdist artifacts
- checks artifact metadata with `twine check`
- validates artifact contents with `scripts/release_preflight.py`
- rejects artifacts that accidentally include repository-only surfaces such as `cortex-sdk/` or `sdks/`

## Pre-Release Expectations

Before cutting a release:

- ensure CI is green
- confirm package metadata is accurate
- confirm user-facing documentation matches shipped behavior
- confirm the PyPI Trusted Publisher is configured exactly for `borjamoskv/Cortex-Persist`, `release.yml`, and environment `pypi`
- confirm any security-sensitive release notes are coordinated privately when needed
- confirm the target release line matches the support posture in [VERSION_SUPPORT.md](VERSION_SUPPORT.md)

## Release Authority

This repository currently follows a maintainer-led release model. Release publication authority is effectively held by the primary maintainer until a broader maintainer structure is documented.

## Rollback And Revocation

If a bad package or release is published:

- stop further promotion of that version
- publish a corrective release rather than silently replacing artifacts
- document the affected release line in public release notes when appropriate
- treat old unsupported lines as forward-fix only unless an exception is stated explicitly

## Supply-Chain Signals

Public supply-chain posture is supported by:

- signed release artifacts
- GitHub Actions provenance
- dependency audit in CI
- SBOM generation
- container image scanning

See [SECURITY.md](SECURITY.md) for the public-facing security summary.
