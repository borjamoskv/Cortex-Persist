# Security

## Supported Versions

| Version | Supported |
|:---|:---:|
| 8.x | ✅ Active |
| 6.x | ⚠️ Security patches only |
| < 6.0 | ❌ No longer supported |

---

## Reporting a Vulnerability

**Do NOT open a public issue for security vulnerabilities.**

Email: **security@cortexpersist.com**

You will receive an acknowledgment within 48 hours and a detailed response within 5 business days.

---

## Security Architecture

CORTEX is built security-first across 7 layers:

### 1. Authentication

- **HMAC-SHA256 API keys** with prefix-based lookup (`ctx_`)
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
- **Immutable transactions** — facts are never physically deleted
- **Cryptographic verification** — any fact can be independently verified

### 5. Privacy Shield (Ingress Guard)

11-pattern secret detection at data ingress:

| Category | Patterns | Severity |
|:---|:---|:---|
| **Critical** | SSH private keys | Blocks cloud storage |
| **Platform** | GitHub tokens, GitLab PATs, Slack tokens | High alert |
| **Standard** | JWT, AWS keys, generic API keys | Warning |

Three-tier scoring system with automatic response:
- Critical secrets → force local-only storage
- Platform secrets → flag and notify
- Standard secrets → log and tag

### 6. AST Sandbox

LLM-generated code is parsed via Python's AST before execution:
- No `eval()`, `exec()`, or `__import__` allowed
- Statement whitelist (assignments, function calls, returns)
- Prevents prompt-injection-to-RCE attacks

### 7. Network Security

- **Security Headers Middleware**: CSP, HSTS, X-Frame-Options, X-Content-Type-Options, X-XSS-Protection
- **Content Size Limit**: Request body capping to prevent DoS
- **Rate Limiting**: Sliding window (300 req/60s per IP, configurable)
- **CORS**: Explicit origin allowlist (no wildcards)
- **Input Validation**: Pydantic models with `max_length` constraints

---

## Secrets Management

### AES-256-GCM Vault

CORTEX provides an encrypted vault for sensitive configuration:

```python
from cortex.crypto import CortexVault

vault = CortexVault(key_path="~/.cortex/vault.key")
vault.encrypt("api_token", "sk-xxx...")
value = vault.decrypt("api_token")
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
| Code injection | AST sandbox for LLM-generated code |
| DoS | Rate limiting + content size limits |
| XSS/CSRF | Security headers middleware |

### What CORTEX Does NOT Protect Against

| Threat | Responsibility |
|:---|:---|
| Physical host compromise | Infrastructure team |
| Network-level attacks | Network security team |
| Social engineering | Organizational policy |
| Key management | Deploying organization |
