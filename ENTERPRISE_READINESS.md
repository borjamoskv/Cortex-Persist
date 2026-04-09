# Enterprise Readiness

This document is the shortest honest path for technical diligence, procurement review, and acquisition-style evaluation of CORTEX Persist.

## Executive Summary

CORTEX Persist is a trust layer for AI agents that focuses on tamper-evident memory, cryptographic lineage, and deterministic write-path validation. The repository shows visible investment in CI, security workflows, and test automation, but those signals still require buyer verification in the target deployment context. It is not yet positioned as a fully mature enterprise platform across every surface, and that distinction matters.

The current public posture is best described as:

- **Product maturity:** advanced beta
- **License posture:** Apache-2.0
- **Primary deployment posture:** source-installed and local-first, with the self-hosted API currently positioned as a beta surface
- **Trust posture:** cryptographic auditability and verification-first design
- **Commercial posture:** promising, but requires buyer-specific diligence on support, roadmap, and productization depth
- **Operational continuity:** maintainer-led, with explicit key-person concentration risk that should be evaluated during diligence

## What A Large Buyer Can Verify Quickly

- **Supported core boundary:** [docs/supported-core.md](docs/supported-core.md)
- **Canonical product proof:** [docs/canonical-demo.md](docs/canonical-demo.md)
- **Security policy:** [SECURITY.md](SECURITY.md)
- **Support policy:** [SUPPORT.md](SUPPORT.md)
- **Version support policy:** [VERSION_SUPPORT.md](VERSION_SUPPORT.md)
- **Release process:** [RELEASE_PROCESS.md](RELEASE_PROCESS.md)
- **Maintainer model:** [MAINTAINERS.md](MAINTAINERS.md)
- **Deployment hardening:** [DEPLOYMENT_HARDENING.md](DEPLOYMENT_HARDENING.md)
- **Reproducible diligence flow:** [DUE_DILIGENCE_CHECKLIST.md](DUE_DILIGENCE_CHECKLIST.md)
- **Repository governance:** [REPO_GOVERNANCE.md](REPO_GOVERNANCE.md)
- **Architecture:** [docs/architecture.md](docs/architecture.md)
- **Security and trust model:** [docs/SECURITY_TRUST_MODEL.md](docs/SECURITY_TRUST_MODEL.md)
- **Optional beta API surface:** [docs/api.md](docs/api.md)
- **Operations guidance:** [docs/OPERATIONS.md](docs/OPERATIONS.md)
- **Contribution and engineering expectations:** [CONTRIBUTING.md](CONTRIBUTING.md)

## Strengths

- **Clear product thesis:** tamper-evident memory for AI agents is specific, differentiated, and easy to position.
- **Trust-first architecture:** the repo consistently treats generative output as conjecture until deterministic validation and ledger recording.
- **Repository-level security signals are visible:** CI, CodeQL, dependency audit, SBOM generation, Trivy image scanning, a tagged release workflow with provenance and artifact-signing, and a public security policy are present.
- **Open-source friendliness:** Apache-2.0 lowers friction for evaluation, integration, and acquisition.
- **Supported core plus visible repo breadth:** the local-first CLI trust path is named explicitly, while broader API, MCP, and multi-agent concepts remain visible for diligence without being misrepresented as fully productized.

## Current Gaps A Serious Buyer Should Note

- **Beta line:** the package is still on a `0.3.x` beta release line, so enterprise claims should be framed as directional rather than contractual.
- **Broad repo surface:** the codebase spans many concepts and experiments; buyers should evaluate against the explicitly named [supported core](docs/supported-core.md) rather than assuming every in-tree surface is productized.
- **Broader repo surfaces remain secondary:** architecture, MCP, and orchestration material are useful for diligence, but the shortest honest proof path is still [Canonical Demo](docs/canonical-demo.md) plus [Supported Core](docs/supported-core.md).
- **Website parity still needs discipline:** the repo now carries the versioned product docs, but the external website should not be treated as canonical until link parity and release parity are kept in sync.
- **Commercial readiness is not the same as technical strength:** support expectations, SLAs, managed-service obligations, and legal/compliance claims still require explicit negotiation and validation.
- **Compliance language should be reviewed by counsel:** references to regulated use cases are useful positioning, but legal review is still necessary before binding claims.

## Acquisition-Style Diligence Checklist

### Technical

- Run CI on a clean clone and inspect workflow coverage in `.github/workflows/`.
- Review critical paths under `cortex/engine`, `cortex/memory`, `cortex/guards`, and `cortex/ledger`.
- Verify installation and smoke-test flows from [README.md](README.md) and [docs/api.md](docs/api.md).
- Run [docs/canonical-demo.md](docs/canonical-demo.md) before reviewing broader repo surfaces.
- Confirm the package metadata in [pyproject.toml](pyproject.toml) matches the intended release and support posture.
- Run the reproducible buyer workflow in [DUE_DILIGENCE_CHECKLIST.md](DUE_DILIGENCE_CHECKLIST.md).

### Security

- Review the public policy in [SECURITY.md](SECURITY.md).
- Inspect trust-boundary documentation in [docs/SECURITY_TRUST_MODEL.md](docs/SECURITY_TRUST_MODEL.md).
- Verify the release workflow, provenance, and artifact signing in [.github/workflows/release.yml](.github/workflows/release.yml).
- Verify CodeQL, dependency audit, SBOM, and container scanning workflows in [.github/workflows/ci.yml](.github/workflows/ci.yml) and [.github/workflows/codeql.yml](.github/workflows/codeql.yml).

### Product And Commercial

- Separate core product capabilities from research or experimental surfaces.
- Confirm which roadmap items are committed vs exploratory in [ROADMAP.md](ROADMAP.md).
- Align support obligations with [SUPPORT.md](SUPPORT.md) before promising customer-facing SLAs.
- Review maintainer concentration and continuity posture in [MAINTAINERS.md](MAINTAINERS.md).
- Review deployment assumptions and hardening gaps in [DEPLOYMENT_HARDENING.md](DEPLOYMENT_HARDENING.md).
- Review public messaging in [README.md](README.md) against actual shipped surfaces.

### Legal And Governance

- Confirm Apache-2.0 compatibility with the buyer's intended distribution model.
- Verify contributor and security-contact processes in [CONTRIBUTING.md](CONTRIBUTING.md), [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md), and [SECURITY.md](SECURITY.md).
- Review ownership posture via [.github/CODEOWNERS](.github/CODEOWNERS).

## Recommended Next Hardening Steps

- Prove the named supported core against pilot deployments and turn that evidence into dated support commitments.
- Tighten the version-support policy from broad beta-line statements into dated release commitments or an explicit LTS/non-LTS policy.
- Add architecture decision records or a formal module ownership map for critical trust surfaces.
- Extend the new diligence checklist with buyer-specific integration tests and threat scenarios.
- Document backup, restore, migration rollback, and disaster-recovery drills in more detail.

## Bottom Line

CORTEX already looks like a serious technical asset. What it needed most was a cleaner public diligence surface. This repository now exposes that surface more clearly, but a large company should treat the repo as a credible beta trust platform with improving governance and diligence surfaces, not as a finished managed enterprise platform.
