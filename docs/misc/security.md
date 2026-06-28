<!-- [C5-REAL] Exergy-Maximized -->
# Security

## Supported Versions

| Version | Supported |
|:---|:---:|
| >= 0.3.0 | ✅ Active |
| < 0.3.0 | ❌ No longer supported |

---

## Reporting a Vulnerability

**Do NOT open a public issue for security vulnerabilities.**

Email: **security@cortexpersist.com**

You will receive an acknowledgment within 48 hours and a detailed response within 5 business days.

---

## Security Architecture

CORTEX is built security-first across 7 layers:

### 1. Authentication

- **Argon2id and SHA-256 API keys** with prefix-based lookup (`ctx_`)
- Keys are hashed before storage — raw keys never persist
- Bootstrap flow: first key requires no auth, subsequent keys require admin
- Bearer token authentication on all API endpoints

### 2. Authorization (RBAC)

Four-role hierarchy with atomic permission scopes:

| Role | Permissions |
|:---|:---|
| `SYSTEM` | Full access to all operations |
| `ADMIN` | `read`, `write`, `manage:keys`, `system:config` |
| `AGENT` | `read`, `write` |
| `VIEWER` | `read` only |

### 3. Multi-Tenant Isolation

- `tenant_id` enforced at all 3 memory layers (L1, L2, L3)
- All queries automatically scoped by authenticated tenant
- No cross-tenant data leakage — verified by isolation tests

### 4. Data Integrity

- **SHA-256 hash-chained ledger** — every mutation is linked to its predecessor
- **Merkle tree checkpoints** — periodic batch verification
- **Versioned and tamper-evident writes** — public fact mutations preserve lineage instead of silently overwriting state
- **Cryptographic verification** — any fact can be independently verified

### 5. Privacy Shield (Ingress Guard)

Multi-tier secret and PII detection at data ingress:

| Category | Examples | Typical response |
|:---|:---|:---|
| **Critical** | Private keys, connection strings, SSH material | Reject or force local-only handling |
| **Sensitive** | PII, platform tokens, cloud credentials | Flag, tag, or notify |
| **Standard** | Generic API credentials and infrastructure tokens | Route conservatively and preserve audit context |

Exact signatures evolve with the runtime, but the stable contract is that
high-risk material is detected early and prevented from flowing into unsafe
storage or sync paths.

### 6. AST Sandbox

LLM-generated code is parsed via Python's AST before execution:
- No `eval()`, `exec()`, or `__import__` allowed
- Statement whitelist (assignments, function calls, returns)
- Prevents prompt-injection-to-RCE attacks

### 7. Network Security

- **Security Headers Middleware**: CSP, HSTS, X-Frame-Options, X-Content-Type-Options, X-XSS-Protection
- **Content Size Limit**: Request body capping to prevent DoS
- **Rate Limiting**: Sliding window (100 req/60s, configurable)
- **CORS**: Explicit origin allowlist (no wildcards)
- **Input Validation**: Pydantic models with `max_length` constraints

### 8. Nemesis Protocol (Algorithmic Immunity)

The **Nemesis Protocol** is CORTEX's autonomic immune system, acting as an internal "red-teaming" monitor:
- **Antibody Ledger**: Persistently records structural anti-patterns and previous failures in `nemesis.md`.
- **Real-time Rejection**: Analyzes every incoming fact and code mutation against the antibody ledger.
- **Hormonal Feedback**: Triggers `ADRENALINE` spikes in the Endocrine system when entropy is detected, forcing immediate corrective focus.
- **Fail-Fast**: Blocks execution of patterns that have previously compromised system integrity (Axiom Ω₅).

### 9. Composition Leakage Shield (Holistic Redaction)

> [!IMPORTANT]
> **Design Target (Planned v7.0)**. The current C5-REAL implementation uses a regex-based static Privacy Shield (Tiers 1-4). The cross-field correlation features below describe the target state.

The **fourth leakage vector** — and the most insidious — is **composition leakage**: two individually innocuous data points that, when combined by an adversary, reconstruct a secret. This is the equivalent of **correlation attacks in differential privacy**.

> [!CAUTION]
> Field-by-field redaction is necessary but insufficient. A deploy address alone is harmless. A contract salt alone is meaningless. Combined, they derive the proxy key.

**Attack surface examples:**

| Data A (innocuous) | Data B (innocuous) | Composed Secret |
|:---|:---|:---|
| Deploy address | Contract salt | Proxy admin key |
| Agent public key | Session nonce | Ephemeral signing key |
| Tenant ID | Merkle root index | Internal topology map |
| API key prefix (`ctx_`) | Hash collision pattern | Full key recovery |

**Mitigations:**

- **Holistic Sensitivity Scoring**: Privacy Shield evaluates facts in *context of existing stored data*, not in isolation. Each new fact is scored against the combinatorial surface of related facts.
- **Cross-Field Correlation Analysis**: At ingress, the classifier queries semantically similar existing facts and computes a *composition risk score* — if two facts together exceed the sensitivity threshold, both are flagged.
- **Conservative Redaction Policy**: Data is treated as secret if it *could* become sensitive when combined with future data. Irreversibility of exposure makes this the only safe default (Axiom Ω₃: Byzantine Default).
- **Temporal Composition Awareness**: A fact stored today may be harmless, but a fact stored tomorrow could retroactively weaponize it. The shield re-evaluates composition risk during periodic REM compaction cycles.

---

## Secrets Management

### AES-256-GCM Vault

CORTEX provides an encrypted vault for sensitive configuration:

```python
from cortex.crypto.vault import Vault

vault = Vault(key=b'your_32_byte_secret_key_or_env_var_fallback')
encrypted = vault.encrypt("sk-xxx...")
value = vault.decrypt(encrypted)
```

### Environment Variables

All sensitive configuration is loaded from environment variables. Never hardcode secrets in code.

See `.env.example` for the complete list.

---

## Threat Model

CORTEX assumes:

1. **Local deployments**: The SQLite database is as secure as the host filesystem
2. **Network APIs**: All endpoints require authentication (API keys or JWT)
3. **Multi-tenant**: Strict tenant isolation enforced at query level
4. **Supply chain**: Dependencies are pinned and audited
5. **Agent trust**: No agent is trusted by default — reputation is earned through the consensus system

### What CORTEX Protects Against

| Threat | Protection |
|:---|:---|
| Memory tampering | SHA-256 hash chain + Merkle verification |
| Unauthorized access | API key auth + RBAC |
| Cross-tenant leakage | Tenant-scoped queries at all layers |
| Secret exposure | Privacy Shield ingress scanning |
| **Composition leakage** | **Holistic cross-field correlation analysis (Planned v7.0)** |
| Code injection | AST sandbox for LLM-generated code |
| DoS | Rate limiting + content size limits |
| XSS/CSRF | Security headers middleware |
| Structural Entropy | Nemesis Protocol (Antibody Rejection) |

### What CORTEX Does NOT Protect Against

| Threat | Responsibility |
|:---|:---|
| Physical host compromise | Infrastructure team |
| Network-level attacks | Network security team |
| Social engineering | Organizational policy |
| Key management | Deploying organization |
