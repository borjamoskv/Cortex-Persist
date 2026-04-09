# Repository Governance

This document explains how CORTEX Persist is governed at the repository level: who owns critical surfaces, how changes are reviewed, and which operating rules matter most for maintainability and trust.

## Governance Goals

Repository governance exists to protect four things:

- **Trust continuity:** cryptographic and audit surfaces must remain reviewable and hard to accidentally weaken
- **Operational clarity:** contributors should know where to file issues, how releases happen, and which documents are authoritative
- **Change safety:** high-risk areas should receive proportionate review and rollback planning
- **Buyer confidence:** outside evaluators should be able to distinguish mature process from raw technical ambition

## Source Documents

The governance model for this repository is distributed across these files:

- [docs/supported-core.md](docs/supported-core.md) for the explicit public product boundary
- [AGENTS.md](AGENTS.md) for operating constraints on autonomous contributors
- [CONTRIBUTING.md](CONTRIBUTING.md) for contributor workflow
- [SECURITY.md](SECURITY.md) for vulnerability intake and security posture
- [SUPPORT.md](SUPPORT.md) for support expectations
- [VERSION_SUPPORT.md](VERSION_SUPPORT.md) for release-line support expectations
- [RELEASE_PROCESS.md](RELEASE_PROCESS.md) for packaging and release flow
- [.github/CODEOWNERS](.github/CODEOWNERS) for review ownership

## Ownership Model

Today the repository is maintained under a primary-maintainer model. That means decision velocity is high, but key-person concentration is also high and should be acknowledged plainly in any diligence process.

For current ownership and stewardship expectations, see [MAINTAINERS.md](MAINTAINERS.md).

## Review Expectations

Changes are expected to scale in scrutiny with their blast radius.

- **Documentation and marketing copy:** lightweight review is acceptable
- **Public API and CLI behavior:** require behavior review and documentation alignment
- **Security, trust, ledger, guard, memory, or migration changes:** require explicit trust-impact review and rollback thinking
- **Release and packaging changes:** require supply-chain awareness and versioning discipline

The pull request template in [.github/pull_request_template.md](.github/pull_request_template.md) is part of the governance system, not a suggestion.

## Trust-Critical Rules

Every governance rule ultimately exists to protect the write path and trust boundary.

1. Do not weaken guards, tenant isolation, or ledger continuity without documenting why.
2. Do not silently relax validation in ways that turn hard failures into permissive writes.
3. Do not treat generated output as trusted state.
4. Do not ship trust-surface changes without a rollback path.
5. Do not represent roadmap or beta capabilities as contractual enterprise commitments.

## Release And Support Posture

CORTEX Persist is currently maintained on a beta release line. Support and release expectations are documented separately so buyers and contributors do not have to infer them from commit history.

- [VERSION_SUPPORT.md](VERSION_SUPPORT.md)
- [RELEASE_PROCESS.md](RELEASE_PROCESS.md)
- [SUPPORT.md](SUPPORT.md)

## Governance Custodian

- **Primary maintainer:** borjamoskv
- **License:** Apache-2.0
- **Repository model:** open-source, maintainer-led, trust-first
