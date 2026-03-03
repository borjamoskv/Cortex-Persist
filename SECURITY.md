# Security Policy

## Supported Versions

| Version | Supported          |
|:--------|:------------------:|
| 0.3.x   | ✅ Active          |
| < 0.3   | ❌ No longer       |

## Reporting a Vulnerability
 ... (omitido por brevedad, solo cambio de versión) ...
sigstore verify identity \
  --cert-oidc-issuer https://token.actions.githubusercontent.com \
  --cert-identity https://github.com/borjamoskv/cortex/.github/workflows/release.yml@refs/tags/v0.3.0b1 \
  cortex_memory-0.3.0b1.tar.gz


### Container Image Scanning

Every CI pipeline run scans the Docker image with **[Trivy](https://trivy.dev/)** for:

- Known CVEs in OS packages and Python dependencies
- **CRITICAL** and **HIGH** severity findings block the build
- Scan results are visible in GitHub Actions logs

### Dependency Auditing

CI runs **[pip-audit](https://github.com/pypa/pip-audit)** on every push to detect known vulnerabilities in Python dependencies. Any finding fails the build.

## Threat Model

CORTEX assumes:

- The local SQLite database is as secure as the host filesystem
- Network APIs require authentication (API keys or JWT)
- Multi-tenant deployments enforce strict tenant isolation via `tenant_id` scoping
- **Untrusted plugins** execute in containerized sandboxes with no host network access
- **Supply chain attacks** are mitigated by Sigstore signing + pip-audit + Trivy

### Attack Vectors & Mitigations

| Vector | Mitigation |
|:---|:---|
| Tampered package on PyPI | Sigstore signature verification |
| Vulnerable dependency | pip-audit in CI, Dependabot alerts |
| Compromised container image | Trivy scan (CRITICAL/HIGH block) |
| Memory tampering | SHA-256 hash chain + Merkle checkpoints |
| Unauthorized access | RBAC + API key + JWT authentication |
| Secret leakage | Privacy Shield (11 regex patterns at ingress) |
| **Composition leakage** | **Holistic cross-field correlation analysis at ingress** |
| Malicious LLM code output | AST Sandbox (no eval/exec) |
| Cross-tenant data access | Tenant ID scoping on all queries |

> **⚠️ Composition Leakage:** Two individually innocuous data points that, when combined by an adversary, reconstruct a secret (e.g., deploy address + contract salt = proxy key). This is the differential privacy analog of correlation attacks. CORTEX's Privacy Shield evaluates facts holistically — not per-field — scoring each new fact against the combinatorial surface of related stored data.
