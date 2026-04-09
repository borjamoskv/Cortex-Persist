# Support

This document defines how to get help, what is currently supported, and what a commercial evaluator should assume by default.

The support boundary starts with [docs/supported-core.md](docs/supported-core.md). Treat broader architecture, MCP, and orchestration material elsewhere in the repository as repository context unless it is explicitly promoted into that supported-core contract.

## Channels

- **Security vulnerabilities:** email [security@cortexpersist.com](mailto:security@cortexpersist.com). Do not open public issues for vulnerabilities.
- **Bug reports and feature requests:** open a GitHub issue in this repository.
- **Private technical diligence or acquisition conversations:** contact [borja@moskv.com](mailto:borja@moskv.com).

## Current Support Posture

CORTEX Persist is maintained as an actively developed open-source project with a beta product line.

Unless separately agreed in writing, this repository does not imply a paid support contract, formal escalation ladder, or managed-service obligation.

| Release line | Status | Support expectation |
| :--- | :--- | :--- |
| `0.3.x` beta | Active | Best-effort bug fixes, security triage, and documentation updates |
| `< 0.3.0` | Unsupported | Upgrade required before support review |

## Response Targets

- **Security reports:** acknowledgment within 48 hours and severity triage within 5 business days
- **Public bug reports:** best effort, prioritized by severity and reproducibility
- **Documentation issues:** best effort, usually batched with the next maintenance pass

These are response targets, not contractual SLAs.

## What Support Covers

- Source-install, local runtime, and documented packaging issues for the supported core
- Reproducible bugs in documented features
- Security report intake and triage
- Clarification of intended behavior for the supported CLI core and the documented beta API surface

## What Support Does Not Automatically Cover

- Custom feature development
- On-call coverage
- Managed hosting or data operations
- Buyer-specific compliance sign-off
- Migration design for heavily customized forks
- Contractual SLAs or guaranteed escalation

## Guidance For Enterprise Evaluation

If you are evaluating CORTEX for regulated or high-stakes use, review these documents together:

- [README.md](README.md)
- [docs/supported-core.md](docs/supported-core.md)
- [ENTERPRISE_READINESS.md](ENTERPRISE_READINESS.md)
- [DUE_DILIGENCE_CHECKLIST.md](DUE_DILIGENCE_CHECKLIST.md)
- [DEPLOYMENT_HARDENING.md](DEPLOYMENT_HARDENING.md)
- [SECURITY.md](SECURITY.md)
- [VERSION_SUPPORT.md](VERSION_SUPPORT.md)
- [RELEASE_PROCESS.md](RELEASE_PROCESS.md)
- [MAINTAINERS.md](MAINTAINERS.md)
- [docs/SECURITY_TRUST_MODEL.md](docs/SECURITY_TRUST_MODEL.md)
- [docs/architecture.md](docs/architecture.md)
- [docs/OPERATIONS.md](docs/OPERATIONS.md)

Align commercial expectations explicitly before treating this repository as a managed platform commitment. The supported product core today remains source-installed and local-first, while the self-hosted API is still beta.
