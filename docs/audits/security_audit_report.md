# CORTEX API Security Audit Report

**Date:** 2026-02-23  
**Auditor:** Automated Security Analysis  
**Version:** CORTEX v4.3 (Wave 5/6)  

---

## Executive Summary

The CORTEX API demonstrates **strong security posture** overall, with well-implemented authentication, parameterized SQL queries, proper tenant isolation, and defensive coding patterns. Most routes are protected with appropriate permission checks. However, several **low-to-medium severity issues** were identified that warrant attention.

| Category | Count | Status |
|----------|-------|--------|
| Critical | 0 | ✅ None found |
| High | 1 | ⚠️ Attention required |
| Medium | 4 | ⚠️ Improvements recommended |
| Low | 5 | ℹ️ Good to address |
| Info/Defense | 3 | ℹ️ Hardening opportunities |

---

## Findings

### 🔴 HIGH SEVERITY

#### 1. Missing Authentication on Export Endpoint (`/v1/projects/{project}/export`)

**Location:** `cortex/routes/admin.py:22-56`

**Description:** The project export endpoint does not require authentication, allowing unauthenticated users to export project data. Additionally, path validation uses string-based checks that could potentially be bypassed.

**Vulnerable Code:**
```python
@router.get("/v1/projects/{project}/export")
async def export_project(
    project: str,
    request: Request,
    path: str | None = Query(None),
    fmt: str = Query("json", alias="format"),
) -> dict:
    # NO AUTHENTICATION CHECK
    if path:
        if any(c in path for c in ("\0", "\r", "\n", "\t")):
            raise HTTPException(status_code=400, detail=get_trans("error_invalid_path_chars", lang))
```

**Impact:** 
- Data exfiltration without authentication
- Potential path traversal if validation is bypassed

**Recommendation:**
```python
@router.get("/v1/projects/{project}/export")
async def export_project(
    project: str,
    request: Request,
    path: str | None = Query(None),
    fmt: str = Query("json", alias="format"),
    auth: AuthResult = Depends(require_permission("admin"))  # ADD THIS
) -> dict:
```

---

### 🟡 MEDIUM SEVERITY

#### 2. Missing Authentication on Handoff Endpoint (`/v1/handoff`)

**Location:** `cortex/routes/admin.py:147-164`

**Description:** The handoff generation endpoint lacks authentication, allowing anyone to generate and save handoff data.

**Vulnerable Code:**
```python
@router.post("/v1/handoff")
async def handoff_generate(
    request: Request,
    engine: CortexEngine = Depends(get_engine),
) -> dict:
    # NO AUTHENTICATION
```

**Impact:** Potential abuse of the handoff system

**Recommendation:** Add `auth: AuthResult = Depends(require_permission("read"))` dependency.

---

#### 3. Unauthenticated Tips Endpoints

**Location:** `cortex/routes/tips.py`

**Description:** All tips endpoints (`/tips`, `/tips/categories`, `/tips/category/{category}`, `/tips/project/{project}`) lack authentication. While tips may be considered public, this creates inconsistency in the API security model.

**Impact:** 
- Inconsistent security posture
- Potential information disclosure about available tip categories and projects

**Recommendation:** Add authentication requirement or document intentional public access.

---

#### 4. Potential Timing Attack on API Key Comparison

**Location:** `cortex/auth.py:141-176`

**Description:** The authentication uses `@lru_cache` which can introduce timing variations that might leak information about whether a key hash exists in the cache vs. requiring a database lookup.

**Code:**
```python
@lru_cache(maxsize=1024)
def authenticate(self, raw_key: str) -> AuthResult:
    # ...
```

**Impact:** Theoretical timing attack risk (low in practice due to SQLite query timing)

**Recommendation:** Consider using a constant-time comparison for the key prefix check and ensure cache hit/miss timing differences are minimized.

---

#### 5. Missing Rate Limit Granularity

**Location:** `cortex/api.py:141-198`

**Description:** The rate limiter tracks by IP only and doesn't distinguish between authenticated and unauthenticated requests. A valid user could be rate-limited by another user sharing the same IP (NAT/proxy scenario).

**Impact:** Legitimate users may be rate-limited unfairly

**Recommendation:** Implement per-API-key rate limiting in addition to IP-based limiting, respecting the `rate_limit` field in the `api_keys` table.

---

### 🟢 LOW SEVERITY

#### 6. CORS Configuration Allows Credentials from Multiple Origins

**Location:** `cortex/api.py:201-207`

**Description:** The CORS middleware allows credentials and uses a list of allowed origins. When credentials are allowed, the wildcard `*` cannot be used, but the current implementation may allow multiple origins which can be risky if not properly validated.

**Code:**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # Multiple origins with credentials
    allow_credentials=True,
    ...
)
```

**Recommendation:** Validate that `ALLOWED_ORIGINS` is strictly controlled in production.

---

#### 7. FTS Query Sanitization Limitations

**Location:** `cortex/search/utils.py:36-44`

**Description:** The FTS5 query sanitizer only removes quotes and basic boolean operators. FTS5 has additional syntax features that may have security implications.

**Code:**
```python
def _sanitize_fts_query(query: str) -> str:
    tokens = query.split()
    safe_tokens = []
    for token in tokens:
        cleaned = token.replace('"', "").replace("'", "")  # Limited sanitization
        if cleaned and cleaned.upper() not in ("AND", "OR", "NOT"):
            safe_tokens.append(f'"{cleaned}"')
```

**Impact:** Potential FTS5 query manipulation (limited impact due to parameterized queries elsewhere)

**Recommendation:** Consider using FTS5's built-in query tokenizer or a more comprehensive sanitization approach.

---

#### 8. Exception Information Disclosure

**Location:** Multiple files

**Description:** Some endpoints may leak internal error details through exception handlers. While the main handlers in `api.py` are safe (returning generic messages), some route-specific handlers may expose details.

**Example in `cortex/routes/admin.py:45-46`:**
```python
except (ValueError, RuntimeError) as e:
    raise HTTPException(status_code=400, detail=f"Invalid path: {e}") from None
```

**Recommendation:** Review all exception handlers to ensure they don't leak sensitive path or system information.

---

#### 9. Tenant ID Injection Risk in Key Creation

**Location:** `cortex/routes/admin.py:86-124`

**Description:** The `create_api_key` endpoint accepts `tenant_id` from query parameters without validation. While this is checked for admin permissions when keys exist, the first bootstrap key allows any tenant_id.

**Code:**
```python
@router.post("/v1/admin/keys")
async def create_api_key(
    request: Request,
    name: str = Query(...),
    tenant_id: str = Query("default"),  # No validation
    ...
```

**Recommendation:** Add validation for tenant_id format (alphanumeric with limited special chars).

---

#### 10. Langbase and Stripe Routes Conditionally Loaded

**Location:** `cortex/api.py:290-301`

**Description:** Langbase and Stripe routes are conditionally loaded based on environment variables. This dynamic loading could potentially be confusing for security audits.

**Recommendation:** Document this behavior clearly in security documentation.

---

### ℹ️ DEFENSE-IN-DEPTH RECOMMENDATIONS

#### 11. No Request Size Limits

**Description:** No explicit request body size limits are configured for the FastAPI application. Large requests could potentially cause DoS.

**Recommendation:** Add request size limits:
```python
app = FastAPI(...)
# Add middleware for request size limiting
```

---

#### 12. Missing Security Headers

**Description:** The API doesn't appear to set security headers like `X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection`, etc.

**Recommendation:** Add security headers middleware.

---

#### 13. API Key in URL Query Parameters

**Description:** While the primary authentication uses the `Authorization` header, some endpoints may accept keys via query parameters (common in webhook scenarios).

**Recommendation:** Ensure API keys are never logged when passed in query parameters.

---

## Positive Security Controls ✅

### 1. **Strong Authentication System**
- API keys use SHA-256 hashing with secure prefix
- Keys are never stored in plaintext
- Proper permission-based access control (`read`, `write`, `admin`)

### 2. **SQL Injection Prevention**
- **All database queries use parameterized statements** - No SQL injection vulnerabilities found
- `cortex/temporal.py` properly validates table aliases using `isalnum()`
- `cortex/graph/backends/sqlite/query.py` uses placeholders correctly

### 3. **Tenant Isolation**
- Strong tenant isolation enforced across all data access
- `cortex/routes/facts.py` properly checks `fact["project"] != auth.tenant_id`
- Tests in `tests/test_consensus_security.py` verify isolation

### 4. **Input Validation**
- Pydantic models with field validators in `cortex/models.py`
- `MCPGuard` in `cortex/mcp/guard.py` provides additional validation
- Path traversal prevention in export endpoint (though auth missing)

### 5. **Secure Defaults**
- Rate limiting enabled by default
- CORS with explicit allow list
- API key format validation (`ctx_` prefix check)

### 6. **Cryptographic Integrity**
- Immutable ledger with SHA-256 hashing
- Merkle tree checkpoints
- Transaction chain verification

### 7. **Error Handling**
- Generic error messages for unhandled exceptions
- Proper logging without sensitive data exposure

---

## Test Coverage

The following security tests exist and pass:

| Test File | Coverage |
|-----------|----------|
| `tests/test_auth.py` | API key creation, authentication, revocation |
| `tests/test_security_hardening.py` | CORS, SQL injection, path traversal, rate limiting |
| `tests/test_consensus_security.py` | Tenant isolation, vote validation |
| `tests/test_api.py` | Authentication requirements for endpoints |

---

## Recommendations Summary

### Immediate Actions (High Priority)
1. ✅ Add authentication to `/v1/projects/{project}/export`
2. ✅ Add authentication to `/v1/handoff`
3. ✅ Document whether `/tips` endpoints should be public

### Short-term (Medium Priority)
4. ✅ Implement per-API-key rate limiting
5. ✅ Add request size limits
6. ✅ Add security headers middleware

### Long-term (Low Priority)
7. ✅ Enhance FTS5 query sanitization
8. ✅ Review and standardize error messages
9. ✅ Add request logging/monitoring for security events

---

## Conclusion

The CORTEX API is **well-architected from a security perspective**. The use of parameterized queries throughout, strong tenant isolation, and proper authentication mechanisms demonstrate good security practices. The primary issues identified are missing authentication on a few endpoints rather than fundamental vulnerabilities.

With the recommended fixes applied, the API will have a robust security posture suitable for production use.

---

*Report generated by automated security analysis.*
