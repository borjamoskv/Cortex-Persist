# CORTEX Governance

> How decisions are made, who maintains what, and how to become a contributor.

## Decision-Making

CORTEX uses **lazy consensus with benevolent dictator (BD) override**:

1. **Proposals** are submitted as GitHub Issues or Discussions
2. **Review period** is 7 days for non-trivial changes
3. If no objections → proposal is accepted
4. If contested → BD (Borja Moskv) has final say
5. **Architecture Decision Records** (ADRs) are kept in `docs/adr/`

## Maintainers

| Role | Person | Scope |
|:---|:---|:---|
| **Lead Maintainer (BD)** | [@borjamoskv](https://github.com/borjamoskv) | Full project — architecture, releases, roadmap |

### Becoming a Maintainer

1. Contribute **3+ merged PRs** touching core modules (`cortex/engine/`, `cortex/consensus/`, `cortex/memory/`)
2. Participate in **2+ architecture discussions**
3. Demonstrate understanding of the trust model (hash chain, Merkle, WBFT)
4. Invited by existing maintainer

### Becoming a Committer

1. Contribute **1+ merged PR** of any scope
2. Follow the code style and testing standards in [CONTRIBUTING.md](CONTRIBUTING.md)
3. Added to the `contributors` team with write access

## Areas Seeking Co-Maintainers

We actively seek co-maintainers for:

| Area | Modules | Skills Needed |
|:---|:---|:---|
| **Distributed Backends** | `cortex/storage/`, `cortex/database/` | PostgreSQL, Qdrant, Redis |
| **SDKs** | `sdks/` | TypeScript, Go |
| **Kubernetes** | `infra/` | Helm, K8s operators |
| **Security** | `cortex/auth/`, `cortex/crypto/` | Cryptography, RBAC |
| **Documentation** | `docs/` | Technical writing |

## Release Process

1. All tests must pass (`pytest tests/ -q`)
2. MEJORAlo score ≥ 80/100
3. CHANGELOG.md updated
4. Tag with semver: `git tag -a vX.Y.Z -m "description"`
5. GitHub Release with auto-generated notes

## Code of Conduct

Be respectful. No harassment or discrimination. See [Contributor Covenant v2.1](https://www.contributor-covenant.org/version/2/1/code_of_conduct/).

## Communication

- **Issues**: Bug reports and feature requests
- **Discussions**: Architecture proposals, RFCs
- **Email**: security@cortexpersist.com (security only)

---

*Governance model v1.0 — effective 2026-02-24*
