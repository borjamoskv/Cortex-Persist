# Release Process

This document describes the tagged public release flow for CORTEX Persist.

## Release Model

CORTEX Persist is currently released through a Python-first tagged workflow. Source installation remains the fallback path until a tagged public release is successfully published.

- version metadata lives in [pyproject.toml](pyproject.toml)
- release tags follow the `v*` pattern
- GitHub Actions builds Python source and wheel artifacts
- GitHub Actions publishes the Python package to PyPI when the tagged workflow runs against the configured release environment
- the in-repo JS SDK is not yet part of the public npm publication path

## Release Workflow

The authoritative workflow is:

- [.github/workflows/release.yml](.github/workflows/release.yml)

At a high level, the workflow:

1. validates release metadata and tag alignment
2. builds Python source and wheel artifacts
3. smoke-tests the built wheel import surface
4. generates build provenance
5. publishes to PyPI
6. signs artifacts with Sigstore
7. uploads signed artifacts and creates the GitHub Release

## Pre-Release Expectations

Before cutting a release:

- ensure CI is green
- confirm package metadata is accurate
- confirm user-facing documentation matches shipped behavior
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

- the tagged Python release workflow
- GitHub Actions provenance
- Sigstore artifact signing in the release workflow
- dependency audit in CI
- SBOM generation
- container image scanning

See [SECURITY.md](SECURITY.md) for the public-facing security summary.
