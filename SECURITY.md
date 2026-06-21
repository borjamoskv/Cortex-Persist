<!-- [C5-REAL] Exergy-Maximized -->
# Security Policy

## Supported Versions

| Version    | Supported          |
|:-----------|:------------------:|
| >= 0.3.0   | ✅ Active          |
| < 0.3.0    | ❌ No longer       |

## Reporting a Vulnerability

**Do NOT open a public issue for security vulnerabilities.**

Please report vulnerabilities by opening a **Private Vulnerability Report** in this GitHub repository or by contacting the maintainer directly.

You will receive an acknowledgment within 48 hours and a detailed response within 5 business days.

## Security Features

CORTEX is built security-first:

- **SHA-256 sovereign ledger continuity** — tamper-evident fact storage
- **Merkle tree checkpoints** — batch integrity verification
- **Privacy Shield** — 11-pattern secret detection and holistic cross-field correlation analysis at ingress
- **AST Sandbox** — safe LLM code execution via deny-by-default structural validation
- **RBAC** — 4-role access control enforcing the principle of least privilege
- **Security Headers Middleware** — CSP, HSTS, X-Frame-Options
- **Input Sanitization** — validated ingress surfaces apply sanitization and schema checks

### Privacy Shield & Composition Leakage

Two individually innocuous data points that, when combined by an adversary, reconstruct a secret (e.g., deploy address + contract salt = proxy key). This is the differential privacy analog of correlation attacks. 

CORTEX's Privacy Shield evaluates facts holistically — not per-field — scoring each new fact against the combinatorial surface of related stored data with the following verifiable bounds:
- **Max Correlation Depth**: Bounded to N=2 hops in the semantic graph.
- **Computational Complexity**: O(k) per insertion by leveraging locality embeddings.
- **False Positives**: Addressed via configurable confidence thresholds.
- **Graph Growth**: Linear scaling through vector proximity clustering prior to combinatorial checking.

### AST Sandbox Architecture

The execution of LLM-generated logic is protected by a strict, deny-by-default whitelist on all JIT compilers. 
- **Allowed Nodes**: `ast.Num`, `ast.Str`, `ast.List`, `ast.Dict`, `ast.Name`, `ast.Assign`, `ast.Call` (with strict target validation).
- **Blocked Functions**: Execution of `getattr`, `globals`, `locals`, `compile`, `__subclasses__`, `eval`, and `exec` is structurally denied.
- **Reflection Escapes**: Access to any attribute starting with `__` is blocked to prevent traversing the interpreter's frame or object hierarchies.

### Role-Based Access Control (RBAC)

CORTEX implements a strict separation of duties enforcing the principle of least privilege:

| Role | Capability Surface | Constraints |
| :--- | :--- | :--- |
| **Viewer** | Read-only access | Scoped to specific `tenant_id` boundaries. |
| **Editor** | Read/Write/Update | Cannot delete cryptographic ledger entries. |
| **Auditor** | Read-only + Ledger Verification | Full visibility into hash chains and ZK-Seals; cannot mutate state. |
| **Admin** | System configuration | Cannot alter the ledger history or bypass sovereign seals. |

## Supply Chain Security

### Cryptographic Contract

The current shipped package uses **SHA-256** for sovereign ledger continuity and
Merkle lineage. Some audit or signature-oriented subsystems also use
**SHA3-256**, but those should not be read as redefining the canonical ledger
continuity algorithm unless the implementation is explicitly migrated.

### Release Signing

The release workflow **signs the built distribution artifacts using [Sigstore](https://sigstore.dev/)** after the publish step. This provides:

- **Provenance verification** — Confirm artifacts were built by our CI pipeline
- **Tamper detection** — Verify packages haven't been modified after signing
- **Keyless signing** — Uses OIDC identity, no long-lived keys to compromise

To verify a release:

```bash
pip install sigstore
sigstore verify identity \
  --cert-oidc-issuer https://token.actions.githubusercontent.com \
  --cert-identity "https://github.com/borjamoskv/Cortex-Persist/.github/workflows/release.yml@refs/tags/v<VERSION>" \
  cortex_persist-<VERSION>.tar.gz
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

- The local SQLite database is as secure as the host filesystem. For enterprise deployments, this implies:
  - **Encryption at rest** (e.g., AES-256-GCM via `cortex/crypto/`).
  - **Signed backups** to preserve ledger continuity.
  - **Key management** via an OS keyring or sovereign vault.
- Network APIs require authentication (API keys or JWT)
- Multi-tenant deployments enforce strict tenant isolation via `tenant_id` scoping
- **Untrusted plugins** execute in containerized sandboxes with no host network access
- **Supply chain attacks** are mitigated by Sigstore signing + pip-audit + Trivy

### Attack Vectors & Mitigations

| Vector | Mitigation |
| :--- | :--- |
| Tampered release artifact | Sigstore signature verification |
| Vulnerable dependency | pip-audit in CI, Dependabot alerts |
| Compromised container image | Trivy scan (CRITICAL/HIGH block) |
| Memory tampering | SHA-256 sovereign hash chain + Merkle checkpoints |
| Unauthorized access | RBAC + API key + JWT authentication |
| Secret leakage | Privacy Shield (11 regex patterns at ingress) |
| **Composition leakage** | **Holistic cross-field correlation analysis at ingress** |
| Malicious LLM code output | AST Sandbox (deny-by-default whitelist on all JIT compilers) |
| Cross-tenant data access | Tenant ID scoping on all queries |
| Shell injection via subprocess | All subprocess calls use `create_subprocess_exec` (no shell=True) |
| Credential leakage in source | No hardcoded secrets; env-var-only credential loading |
| CORS misconfiguration | Wildcard `*` rejected in cloud/production deployment mode |
| Unsafe file patching | AST validation gate before writing patches to `.py` files |

> **⚠️ Composition Leakage:** Refer to the "Privacy Shield & Composition Leakage" section above for details on depth, complexity, and scaling limits for correlation attacks.

---

## Security Audit Log

### 2026-05-26 — Static Analysis Audit (C4-SIM)

**Scope:** 28 core modules (~8,500 LOC)

| Severity | Count | Status |
|:---|:---:|:---|
| Critical | 3 | ✅ Remediated |
| High | 5 | ✅ Remediated |
| Medium | 4 | ✅ Remediated |
| Low | 6 | 📋 Documented |

**Critical findings remediated:**
1. Demiurge JIT `exec()` without AST validation — now gates via `ASTSandbox`
2. Sortu JIT `__import__` in safe_builtins — removed (ACE vector)
3. Ouroboros `os.system()` with unsanitized path — migrated to `subprocess.run()`

---

## Related Security Documentation

For trust boundaries, verification flow, ledger continuity, and cognitive/state-mutation
security surfaces, see
[`docs/SECURITY_TRUST_MODEL.md`](./docs/SECURITY_TRUST_MODEL.md).

