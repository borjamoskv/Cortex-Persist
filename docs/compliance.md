<!-- [C5-REAL] Exergy-Maximized -->
# EU AI Act & SOC 2 Compliance

**Document Version:** 2.1
**Date:** 2026-06-19
**System:** CORTEX Trust Engine v1.0.0 (Apache-2.0)

---

## Scope

This document maps CORTEX Trust Engine capabilities to the requirements of the **EU AI Act (Regulation 2024/1689)**, specifically **Article 12** (Record-Keeping) and related provisions for high-risk AI systems, as well as the **AICPA SOC 2 Type II** Trust Services Criteria.

**EU AI Act Enforcement Date:** August 2, 2026

**Potential Fines:** €30 million or 6% of global annual revenue.

---

## Article 12 — Record-Keeping

### Art. 12.1 — Automatic Logging of Events

| Requirement | CORTEX Implementation | Evidence |
|:---|:---|:---|
| High-risk AI systems shall technically allow for the automatic recording of events (logs) | Every `store()` operation creates a transaction in the immutable ledger with SHA-256 hash linking | `cortex/engine/ledger.py` — `ImmutableLedger` |
| Logs shall be generated throughout the lifetime of the system | Transaction ledger operates continuously; every fact insertion, update, or deletion is recorded | `transactions` table |

**Verification:** `cortex audit-trail`

### Art. 12.2 — Content of Logs

| Requirement | CORTEX Implementation | Evidence |
|:---|:---|:---|
| Recording of the period of each use | `created_at` timestamp on every fact and transaction | `facts.created_at`, `transactions.timestamp` |
| Reference database against which input data has been checked | Project-scoped fact database with full history | `facts.project` scoping |
| Input data for which the search has led to a match | Search results include `fact_id`, `score`, and `content` | `/v1/search` endpoint |

### Art. 12.2d — Agent Traceability

| Requirement | CORTEX Implementation | Evidence |
|:---|:---|:---|
| Identification of agents involved in verification | Agent tagging system with automatic source detection | `facts.source`, `facts.tags` |
| Agent responsibility tracking | Consensus votes linked to agent IDs with reputation weights | `consensus_votes_v2` table |

**Verification:** `cortex compliance-report`

### Art. 12.3 — Tamper-Proof Storage

| Requirement | CORTEX Implementation | Evidence |
|:---|:---|:---|
| Logs shall be kept for an appropriate period | Facts are never physically deleted (soft-delete via `valid_until`) | `facts.valid_until` field |
| Logs must be tamper-evident | SHA-256 hash chain: each transaction includes the previous hash | `transactions.hash`, `transactions.prev_hash` |
| Integrity must be verifiable | Merkle tree checkpoints enable O(log N) batch verification | `merkle_roots` table |

**Verification:**

- `cortex verify <fact_id>` — Single fact verification certificate
- `cortex ledger verify` — Full chain integrity check

### Art. 12.4 — Periodic Verification

| Requirement | CORTEX Implementation | Evidence |
|:---|:---|:---|
| Providers shall implement means for periodic integrity verification | Merkle tree checkpoints created at configurable intervals | `ImmutableLedger.create_checkpoint_sync()` |
| Verification results shall be recorded | `integrity_checks` table stores every verification result | `integrity_checks` table |

**Verification:** `cortex compliance-report`

---

## SOC 2 Type II — Trust Services Criteria Mapping

CORTEX Persist provides native architectural support for SOC 2 Type II compliance, specifically addressing the Security, Availability, and Confidentiality criteria.

### 1. Security (Logical Access & Protection)

| Criterion (CC) | CORTEX Implementation | Evidence |
|:---|:---|:---|
| **CC6.1:** Logical access security | Multi-tenant isolation via cryptographic scoping. Z3 SMT Guards prevent unauthorized state mutations. | `legacy_research/guards/zk_guard.py` |
| **CC6.8:** Prevention of unauthorized execution | All mutations require `CORTEX-TAINT` signature. Unsigned executions are aborted at SAGA-1. | `cortex/engine/causal/taint_engine.py` |
| **CC7.2:** Security event logging | Immutable SHA-256 hash-chaining of all `store()` operations. Cryptographically tamper-evident. | `ImmutableLedger` |

### 2. Availability (System Resilience)

| Criterion (CC) | CORTEX Implementation | Evidence |
|:---|:---|:---|
| **CC9.1:** Business continuity and recovery | `ROLLBACK_STATE` SAGA compensation ensures atomic recovery from failure. Postgres WAL / SQLite WAL ensures zero-data-loss durability. | Saga Protocol (`cortex/engine/`) |

### 3. Confidentiality (Data Protection)

| Criterion (CC) | CORTEX Implementation | Evidence |
|:---|:---|:---|
| **CC6.6:** Logical boundary protection | 11-pattern ingress guard intercepts PII, PHI, and credentials before persistence. | `cortex/security/ingress.py` |
| **CC6.7:** Data encryption | Ephemeral key destruction in SAGA-4. Sensitive payloads encrypted at rest (AES-GCM). | `cortex/crypto/aes.py` |

---

## Additional Compliance Features

### Decision Lineage (Explainability)

CORTEX maintains a `decision_edges` graph that links decisions chronologically within projects. This enables full **chain-of-reasoning reconstruction** — a key requirement for explainability audits.

**MCP Tool:** `cortex_decision_lineage`

### Multi-Agent Consensus (Art. 14 — Human Oversight)

The **Reputation-Weighted Consensus (RWC)** system allows multiple agents to verify facts before they become canonical:

- Agent reputation scores (0.0–1.0) with decay
- Domain-specific vote multipliers
- Byzantine fault tolerance — works even when agents lie
- Elder Council verdict for edge cases without quorum

**Implementation:** `cortex/consensus/` module

### Data Sovereignty (GDPR Art. 22)

CORTEX is **100% local-first** (SQLite). No data leaves the deployment environment. This inherently satisfies data residency and sovereignty requirements.

For cloud deployments, multi-tenant isolation ensures data boundaries with cryptographic scoping.

### Privacy Shield

The 11-pattern ingress guard detects and flags sensitive data before storage:

- GitHub/GitLab tokens
- JWT tokens
- SSH private keys
- Slack/AWS credentials
- Generic API keys

Critical secrets force **local-only storage** regardless of configuration.

---

## Compliance Score

```bash
$ cortex compliance-report

  CORTEX Compliance Report — EU AI Act Article 12
  ================================================

  ✅ Art. 12.1 — Automatic Logging         COMPLIANT
  ✅ Art. 12.2 — Log Content                COMPLIANT
  ✅ Art. 12.2d — Agent Traceability        COMPLIANT
  ✅ Art. 12.3 — Tamper-Proof Storage       COMPLIANT
  ✅ Art. 12.4 — Periodic Verification      COMPLIANT

  Compliance Score: 5/5
  🟢 COMPLIANT — All Article 12 requirements met.
```

---

## Limitations

1. **No formal audit:** This mapping has not been reviewed by a certified EU AI Act auditor.
2. **High-risk classification:** Whether a system using CORTEX qualifies as "high-risk" depends on its use case, not on CORTEX.
3. **Organizational measures:** CORTEX provides technical measures only. Organizational compliance (policies, training, governance) is the deployer's responsibility.
4. **Legal advice:** This document is for informational purposes. Consult legal counsel for binding compliance guidance.

---

*Prepared by MOSKV Systems · Contact: security@cortexpersist.com*
