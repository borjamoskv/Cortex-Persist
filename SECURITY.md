# Security Policy

## Supported Versions

| Version | Supported          |
|:--------|:------------------:|
| 8.x     | ✅ Active          |
| < 8.0   | ❌ No longer       |

## Reporting a Vulnerability

**Do NOT open a public issue for security vulnerabilities.**

Email: **security@cortexpersist.com**

You will receive an acknowledgment within 48 hours and a detailed response within 5 business days.

## Security Features

CORTEX is built security-first:

- **SHA-256 hash-chained ledger** — tamper-evident fact storage
- **Merkle tree checkpoints** — batch integrity verification
- **Privacy Shield** — 11-pattern secret detection at ingress
- **AST Sandbox** — safe LLM code execution without `eval()`
- **RBAC** — 4-role access control (admin, editor, viewer, auditor)
- **Security Headers Middleware** — CSP, HSTS, X-Frame-Options
- **Input Sanitization** — all user inputs validated and escaped

## Supply Chain Security

### Release Signing

All CORTEX releases published to PyPI are **cryptographically signed using [Sigstore](https://sigstore.dev/)**. This provides:

- **Provenance verification** — Confirm artifacts were built by our CI pipeline
- **Tamper detection** — Verify packages haven't been modified after signing
- **Keyless signing** — Uses OIDC identity, no long-lived keys to compromise

To verify a release:

```bash
pip install sigstore
sigstore verify identity \
  --cert-oidc-issuer https://token.actions.githubusercontent.com \
  --cert-identity https://github.com/borjamoskv/cortex/.github/workflows/release.yml@refs/tags/v8.0.0 \
  cortex_memory-8.0.0.tar.gz
```

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
| Malicious LLM code output | AST Sandbox (no eval/exec) |
| Cross-tenant data access | Tenant ID scoping on all queries |
