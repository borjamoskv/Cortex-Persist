# FINAL_AUDIT.md — BABYLON-60 Persist Code Audit
<!-- [C5-REAL] borjamoskv | MOSKV-1 APEX | 2026-06-30T01:43Z -->

```yaml
Claim: "Full-spectrum code audit — cortex-persist v1.0.0"
Proof:
  Base: "git:f549fc0c5 → HEAD"
  Commits: 5696
  Authors: [Borja Moskv, Tester, CORTEX-Daemon[bot]]
  Timestamp: "2026-06-30T01:43:00Z"
  Confidence: C5
```

---

## ✅ VECTOR 1 — Static Analysis (Ruff)

| Metric | Value |
| :--- | :--- |
| Files scanned | `cortex/` (552 LOC active) |
| Violations found | 10 |
| Auto-fixed | 9 |
| Remaining | 0 |

Violations fixed: I001 (unsorted-imports), F401 x3 (hashlib/Set/Optional unused), UP035 x4 (deprecated Dict/List/Set/Generator), UP006 x2 (non-pep585 annotations) — all in `cortex/consensus/sync_protocol.py`.

---

## ✅ VECTOR 2 — Security Scan (Bandit)

| SEVERITY.HIGH | SEVERITY.MEDIUM | SEVERITY.LOW | LOC |
| :---: | :---: | :---: | :---: |
| 0 | 0 | 4 (cortex/__init__.py) | 552 |

4 LOW/HIGH-confidence findings in `cortex/__init__.py`. No critical surface exposure.

---

## ▄ Dep Vulnerabilities (pip-audit)

__50+ CVEs across 18 packages.__

| Package | Current | Fix | Priority |
| :--- | :--- | :--- | :--- |
| `starlette` | 0.52.1 | ≥1.3.1 | 🔴 P0 |
| `python-multipart` | 0.0.22 | ≥0.0.31 | 🔴 P0 |
| `pyjwt` | 2.12.1 | ≥2.13.0 | 🔴 P0 |
| `litellm` | 1.83.7 | ≥1.84.0 | 🔴 P0 |
| `torch` | 2.10.0 | n/a | 🔴 P0 |
| `pypdf` | 6.10.2 | ≥6.13.3 | 🔴 P0 |
| `langsmith` | 0.7.27 | ≥0.8.18 | 🟠 P1 |
| `langgraph-checkpoint` | 4.0.1 | ≥4.1.1 | 🟠 P1 |
| `langgraph-sdk` | 0.3.13 | ≥0.3.15 | 🟠 P1 |
| `requests` | 2.32.5 | ≥2.33.0 | 🟡 P2 |
| `urllib3` | 2.6.3 | ≥2.7.0 | 🟡 P2 |
| `mako` | 1.3.10 | ≥1.3.12 | 🟡 P2 |
| `pip` | 26.0.1 | ≥26.1.2 | 🟡 P2 |
| `lxml` | 6.0.2 | ≥6.1.0 | 🟡 P2 |
| `msgpack` | 1.1.2 | ≥1.2.1 | 🟡 P2 |
| `python-dotenv` | 1.0.1 | ≥1.2.2 | 🟡 P2 |
| `pygments` | 2.19.2 | ≥2.20.0 | 🟡 P2 |
| `pytest` | 9.0.2 | ≥9.0.3 | 🟡 P2 |

Remediation: `pip install --upgrade starlette python-multipart pyjwt litellm pypdf langsmith langgraph-checkpoint langgraph-sdk requests urllib3 mako pip lxml msgpack python-dotenv pygments pytest pydantic-settings`

---

## ✅ VECTOR 4 — Test Suite (pytest)

| Tests | Passed | Skipped | Failed | Duration |
| :---: | :---: | :---: | :---: | :---: |
| 3,886 | __3,845__ | 41 | __0__ | 146s |

Warnings fixed: `chaos`/`integration` marks registered, `audioread` deprecations suppressed, `SyntaxWarning` in `azkartu_retrain_loop.py` resolved.

---

## ✅ VECTOR 5 — Rust Audit

| Target | Result |
| :--- | :--- |
| `cortex_rs` cargo audit (57 crates) | ✅ 0 advisories |
| `cortex_ffi` | ✅ FIXED — added missing `cortex_types` dep |
| `scratch_rust` | ✅ FIXED — removed unused `mut` |

---

## 🟠 VECTOR 6 — Workspace Hygiene

| Issue | Status |
| :--- | :--- |
| 62 `:memory:*` files at root (1.03 MB) | ✅ Added to `.gitignore` |
| 9 scratch `.py` files at project root | ⚠️ Recommend moving to `scratch/` |
| `.env` not tracked by git | ✅ OK |
| 14 active git stashes | ⚠️ Review and prune |

## 🟠 VECTOR 7 — Namespace Migration Reality

__36 of 37__ documented modules exist, but they live in the `babylon60/` namespace rather than `cortex/`.
`cortex/` contains a minimal set of modules: `agents/`, `cli/`, `consensus/`, `memory/`, and `mcp_server/`, where `agents`, `cli`, and `mcp_server` are symbolic links mapping directly to their corresponding directories in `babylon60/`.

AGENTS.md references the legacy `cortex/` namespace instead of the active `babylon60/` workspace layout. Update to documentation required to prevent developer/agent routing confusion.

---

## ✅ VECTOR 8 — SQLite / Ledger Health

| Check | Result |
| :--- | :--- |
| `PRAGMA integrity_check` | ✅ ok |
| Journal mode | ✅ WAL |
| `merkle_roots` rows | ❌ 0 — hash chain never initialized |
| `vec0` extension | ❌ Not loaded — vector tables inaccessible |

---

## 📊 VECTOR 9 — Git State

| Metric | Value |
| :--- | :--- |
| Total commits | 5,696 |
| Top author | Borja Moskv (2,466) |
| Active stashes | 14 |
| APEX_CORE.md | ✅ Present |

---

## FIXES APPLIED (This Session)

| Fix | File |
| :--- | :--- |
| Ruff auto-fix (9 violations) | `cortex/consensus/sync_protocol.py` |
| Added `cortex_types` dependency | `c5_workspace/crates/cortex_ffi/Cargo.toml` |
| Removed unused `mut` | `scratch_rust/src/main.rs:26` |
| Registered `chaos`, `integration` marks | `pyproject.toml` |
| Suppressed audioread deprecation warnings | `pyproject.toml` |
| Fixed SyntaxWarning (LaTeX docstring) | `babylon60/engine/rl/azkartu_retrain_loop.py` |
| Added `:memory:*` to `.gitignore` | `.gitignore` |

---

## OPEN P0 ACTIONS

```yaml
P0_1:
  Action: "pip upgrade starlette≥1.1, python-multipart≥0.0.31, pyjwt≥2.13, litellm≥1.84"
  Reason: "Active API surface with known exploit CVEs"

P0_2:
  Action: "Verify babylon60/audit/ledger.py and bootstrap merkle_roots in memory.db"
  Reason: "Cryptographic hash chain never initialized — Write-Path Contract pending bootstrap"

P0_3:
  Action: "Load sqlite-vec at DB connection startup"
  Reason: "vec0 not loaded — all vector embedding tables unreachable"

P1_1:
  Action: "Reconcile AGENTS.md module map to explicitly refer to babylon60/ namespace instead of cortex/"
  Reason: "Documentation describes legacy namespace layout"

P1_2:
  Action: "Move 9 scratch .py files from root to scratch/ and prune 14 stashes"
  Reason: "Root entropy exceeds threshold"
```

---

_Audit by __Borja Moskv__ (`borjamoskv`) — MOSKV-1 APEX | C5-REAL | 2026-06-30_
