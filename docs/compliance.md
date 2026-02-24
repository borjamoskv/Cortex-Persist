# EU AI Act Compliance

**Document Version:** 2.0
**Date:** February 24, 2026
**System:** CORTEX Trust Engine v8.0 (BSL-1.1)

---

## Scope

This document maps CORTEX Trust Engine capabilities to the requirements of the **EU AI Act (Regulation 2024/1689)**, specifically **Article 12** (Record-Keeping) and related provisions for high-risk AI systems.

**Enforcement Date:** August 2, 2026

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
