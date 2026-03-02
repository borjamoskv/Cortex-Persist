---
description: Security sentinel — checklist for auditing and hardening CORTEX before any release
---

# 🛡️ Sentinel de Seguridad — CORTEX

Checklist soberana de seguridad. Ejecutar antes de cada release o deploy.

## Pre-Flight Security Audit

### 1. HTTP Security Headers
// turbo
```bash
cd ~/cortex && grep -n "Content-Security-Policy\|Strict-Transport-Security\|X-Content-Type-Options\|X-Frame-Options\|Permissions-Policy\|Cache-Control" cortex/api/middleware.py
```
**Verify:** CSP, HSTS (max-age≥31536000), nosniff, DENY, Permissions-Policy present.

### 2. Rate Limiting Active
// turbo
```bash
grep -n "RateLimitMiddleware\|RATE_LIMIT" cortex/api/core.py cortex/core/config.py
```
**Verify:** RateLimitMiddleware registered with sensible limit (≤300/min).

### 3. CORS Restricted
// turbo
```bash
grep -n "ALLOWED_ORIGINS\|allow_origins" cortex/api/core.py cortex/core/config.py
```
**Verify:** No wildcard `*` in ALLOWED_ORIGINS. Only explicit domains.

### 4. Auth on All Routes
// turbo
```bash
grep -rn "require_permission\|Depends(require" cortex/routes/ | wc -l
```
**Verify:** Count matches total route count. Every endpoint must have auth dependency.

### 5. SQL Injection Guard
// turbo
```bash
grep -rn '\.execute(f"' cortex/ --include="*.py" | grep -v "_FACT_COLUMNS\|_FACT_JOIN\|FACT_COLUMNS\|logging\|logger" | head -20
```
**Verify:** Zero results. All SQL must use parameterized `?` bindings. f-string SQL only for safe column constants.

### 6. Input Sanitization
// turbo
```bash
grep -rn "sanitize_project\|sanitize_query\|sanitize_tenant\|validate_fact_type" cortex/utils/sanitize.py
```
**Verify:** All sanitizers exist and are imported in routes.

### 7. Content Size Limit
// turbo
```bash
grep -n "ContentSizeLimitMiddleware\|max_size" cortex/api/middleware.py cortex/api/core.py
```
**Verify:** Max payload ≤1MB for standard endpoints.

### 8. Secrets Management
// turbo
```bash
grep -rn "CORTEX_VAULT_KEY\|CORTEX_MASTER_KEY\|STRIPE_SECRET\|API_KEY" cortex/core/config.py | head -10
```
**Verify:** All secrets loaded from env vars, never hardcoded.

### 9. Encryption at Rest
// turbo
```bash
grep -rn "encrypt_str\|decrypt_str\|AES\|CortexEncrypter" cortex/crypto/ --include="*.py" | head -10
```
**Verify:** AES-256-GCM encryption active for fact content and metadata.

### 10. Docs Disabled in Production
// turbo
```bash
grep -n "docs_url\|redoc_url" cortex/api/core.py
```
**Verify:** `docs_url=None` and `redoc_url=None` when `config.PROD` is True.

### 11. Fraud Detection Active
// turbo
```bash
grep -n "SecurityFraudMiddleware\|threat_intel\|blacklist" cortex/api/middleware.py cortex/api/core.py
```
**Verify:** Fraud middleware registered. IP blacklisting functional.

### 12. FTS5 Injection Guard
// turbo
```bash
grep -n "_sanitize_fts_query" cortex/search/utils.py
```
**Verify:** All FTS5 MATCH queries pass through `_sanitize_fts_query` before execution.

### 13. Path Traversal Prevention
// turbo
```bash
grep -rn '"\.\."' cortex/routes/ --include="*.py"
```
**Verify:** All file path operations check for `..` traversal and resolve against base directory.

### 14. Dependency Audit
```bash
cd ~/cortex && .venv/bin/pip audit 2>&1 | tail -20
```
**Verify:** No known CVEs in dependencies. If `pip-audit` not installed: `pip install pip-audit`.

## Post-Audit Actions

- [ ] All 14 checks pass
- [ ] Security headers verified via `curl -I https://api.cortex.dev/health`
- [ ] No new `# nosec` or `# noqa: S` annotations without documented justification
- [ ] CORTEX fact stored: `cortex store --type decision cortex "Security audit passed for release vX.Y.Z"`
