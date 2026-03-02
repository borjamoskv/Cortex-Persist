Now I have a comprehensive understanding of the codebase. Let me provide the code review:

---

# 🔍 CODE REVIEW: CORTEX Recent Changes

## Summary

| Category | Count |
|----------|-------|
| **P0 - Critical** | 1 |
| **P1 - High** | 2 |
| **P2 - Medium** | 2 |
| **P3 - Low** | 3 |

---

## P0 🔴 CRITICAL

### 1. `sovereign-deploy.yml`: Secrets Leaked in Logs (Lines 131-141)
**File:** `.github/workflows/sovereign-deploy.yml`

```yaml
echo '${{ secrets.GCP_SA_KEY }}' | docker login -u _json_key --password-stdin gcr.io
aws ecr get-login-password --region eu-west-1 | docker login ...
docker login ${{ secrets.AZURE_ACR_REGISTRY }} -u ${{ secrets.AZURE_ACR_USER }} -p ${{ secrets.AZURE_ACR_PASSWORD }}
```

**Issue:** Docker login commands with `--password-stdin` and `-p` flag may leak credentials in GitHub Actions logs if commands fail or in process listings. The Azure login uses `-p` (password) directly on command line which is visible in `ps` output.

**Fix:** Use proper secret masking and environment variables:
```yaml
env:
  GCP_SA_KEY: ${{ secrets.GCP_SA_KEY }}
run: |
  echo "$GCP_SA_KEY" | docker login -u _json_key --password-stdin gcr.io
```

---

## P1 🟠 HIGH

### 2. Migration 016: Missing Hash Backfill for Existing Facts
**File:** `cortex/migrations/mig_hash.py`

**Issue:** The migration adds the `hash` column but doesn't populate it for existing facts. This causes:
1. Deduplication to fail for pre-existing facts (hash is NULL, not compared)
2. Unique partial index `idx_facts_hash` won't apply to rows with NULL hash
3. **Data inconsistency:** New facts get deduped, old facts don't

**Fix:** Add backfill logic:
```python
def _migration_016_add_fact_hash(conn: sqlite3.Connection):
    # ... existing column add ...
    
    # Backfill hashes for existing facts
    cursor = conn.execute("SELECT id, content FROM facts WHERE hash IS NULL")
    for fact_id, content in cursor.fetchall():
        f_hash = compute_fact_hash(content)
        conn.execute("UPDATE facts SET hash = ? WHERE id = ?", (f_hash, fact_id))
    
    logger.info("Migration 016: Backfilled %d hashes", cursor.rowcount)
```

### 3. `store_mixin.py`: Hash Computed on Encrypted Content (Lines 149-150, 356-357)
**File:** `cortex/engine/store_mixin.py`

**Issue:** The `_check_dedup` method computes hash on **plaintext** content, but the INSERT stores the hash alongside **encrypted** content. If encryption produces different ciphertexts for the same plaintext (due to different nonces/IVs), the dedup logic is correct (comparing plaintext hashes), BUT there's a subtle bug:

- Line 149: `f_hash = compute_fact_hash(content)` - uses plaintext
- Line 356: `f_hash = compute_fact_hash(content)` - uses plaintext

**However**, if content has leading/trailing whitespace that gets stripped AFTER hash computation, dedup could fail. Looking at code flow:
1. `_store_impl` calls `_validate_content` (strips whitespace)
2. But `_check_dedup` is called BEFORE `_validate_content` in store()

**Actually the bug is:** `_check_dedup` uses unstripped content, while stored content is stripped. Same content with different whitespace won't match.

**Fix:** Ensure consistent content normalization before hash computation:
```python
content = self._validate_content(project, content, fact_type)  # First
f_hash = compute_fact_hash(content)  # Then hash
existing_id = await self._check_dedup(conn, tenant_id, project, content, f_hash)  # Pass pre-computed hash
```

---

## P2 🟡 MEDIUM

### 4. `sovereign-deploy.yml`: Terraform Apply Without Plan Review (Lines 186-194)
**File:** `.github/workflows/sovereign-deploy.yml`

**Issue:** `terraform apply -auto-approve tfplan` auto-approves infrastructure changes on every main branch push. No human approval gate for infrastructure changes.

**Fix:** Add environment protection:
```yaml
deploy:
  environment:
    name: production
    url: ${{ steps.deploy.outputs.url }}
```

### 5. Test Coverage Gap: No Hash-Specific Tests
**Files:** `tests/test_purge.py`, `tests/test_api.py`

**Issue:** The dedup tests (`test_dedup_returns_existing_id`, `test_dedup_different_projects_are_separate`) pass because the engine works, but there are no explicit tests for:
- Hash column population
- Hash-based deduplication logic
- Migration 016 applying correctly to existing DBs

**Fix:** Add dedicated test:
```python
def test_hash_column_populated(self, engine):
    fact_id = engine.store_sync("test", "Content for hash verification")
    conn = engine._get_sync_conn()
    row = conn.execute("SELECT hash FROM facts WHERE id = ?", (fact_id,)).fetchone()
    assert row[0] is not None
    assert len(row[0]) == 64  # SHA-256 hex
    assert row[0] == compute_fact_hash("Content for hash verification")
```

---

## P3 🟢 LOW

### 6. `sovereign-deploy.yml`: Unused Trivy Scan Result (Lines 107-115)
**File:** `.github/workflows/sovereign-deploy.yml`

**Issue:** Trivy scan generates `trivy-report.sarif` but it's not uploaded to GitHub Security tab or artifact storage. The scan fails the build on CRITICAL/HIGH but results aren't visible.

**Fix:** Add upload step:
```yaml
- name: Upload Trivy scan results
  uses: github/codeql-action/upload-sarif@v3
  if: always()
  with:
    sarif_file: trivy-report.sarif
```

### 7. `sovereign-deploy.yml`: Hardcoded Power Threshold (Lines 224-232)
**File:** `.github/workflows/sovereign-deploy.yml`

**Issue:** Smoke test asserts `power >= 1300` which is a "breached theoretical limit" per commit history. This is a magic number with no context.

**Fix:** Make it configurable:
```yaml
env:
  SOVEREIGN_POWER_THRESHOLD: "1300"
```

### 8. `flake8`: Per-File Ignore Too Broad (Line 5)
**File:** `.flake8`

**Issue:** `cortex/cli/__init__.py:F401,E402` ignores **all** F401 (unused imports) and E402 (module level import not at top). This could hide real issues.

**Fix:** Use more specific ignores or `noqa` comments on specific lines.

---

## ✅ Correctness Verification

| Component | Status | Notes |
|-----------|--------|-------|
| Schema `hash` column | ✅ | Correctly defined as `TEXT` (nullable) |
| Migration 016 order | ✅ | Properly registered as #16 in registry |
| INSERT statement | ✅ | 13 columns, 13 values, correct order |
| Unique partial index | ✅ | Correctly excludes NULL hashes and deprecated facts |
| test_api.py | ✅ | All 12 tests pass |

---

## Recommendations

1. **Immediate (P0):** Fix secrets exposure in CI workflow
2. **Before next release (P1):** Add hash backfill migration and fix content normalization order
3. **Technical debt (P2):** Add environment protection and hash-specific tests
4. **Polish (P3):** Upload security scan results, make thresholds configurable
