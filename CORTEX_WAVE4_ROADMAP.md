# CORTEX V4.0 — Wave 4 Roadmap & Strategic Analysis

**Date:** 2026-02-16  
**Version Analyzed:** 4.0.0a1  
**Classification:** Strategic Architecture Document  

---

## Executive Summary

This document analyzes the current CORTEX V4.0 implementation, focusing on:
1. **Consensus Layer** — Neural Swarm Consensus with Reputation-Weighted evolution
2. **NotebookLM Prepper** — Knowledge synthesis pipeline for NotebookLM ingestion
3. **Contradictions** — Architectural tensions between competing requirements
4. **Wave 4 Roadmap** — Prioritized next steps for Sovereign AI readiness

---

## 1. Consensus Layer Analysis

### 1.1 Current Implementation Status

| Component | Status | Location |
|-----------|--------|----------|
| Base Consensus (v1) | ✅ Implemented | `cortex/engine.py:569-626` |
| Consensus Votes Table | ✅ Implemented | `cortex/schema.py:122-132` |
| RWC Schema (v2) | ✅ Implemented | `cortex/schema.py:134-197` |
| Agent Registry | ✅ Implemented | `cortex/routes/agents.py` |
| Vote API (v1) | ✅ Implemented | `cortex/routes/facts.py:77-116` |
| Vote API (v2) | ⚠️ Partial | `cortex/routes/facts.py:119-159` (missing `VoteV2Request` import) |
| Migration 009 (RWC) | ✅ Implemented | `cortex/migrations.py:196-248` |

### 1.2 Implementation Gaps Identified

```python
# BUG: facts.py imports VoteV2Request but it's not imported at the top
# Line 122: req: VoteV2Request - but VoteV2Request not in imports
# Missing: from cortex.models import VoteV2Request

# BUG: Engine method vote_v2() referenced but not implemented
# Line 141: api_state.engine.vote_v2(...) - method doesn't exist in engine.py
```

### 1.3 Consensus Architecture Comparison

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CONSENSUS LAYER EVOLUTION                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  V1: LINEAR (Current Active)        V2: REPUTATION-WEIGHTED (Schema Ready)  │
│  ┌─────────────────────────┐        ┌─────────────────────────┐             │
│  │ Score = 1.0 + Σ(v)×0.1  │        │ Score = Σ(v×r×d) / Σ(r) │             │
│  │                         │        │                         │             │
│  │ • Equal weight votes    │        │ • Reputation-weighted   │             │
│  │ • Simple sum            │        │ • Temporal decay        │             │
│  │ • Fixed thresholds      │        │ • Dynamic thresholds    │             │
│  │ • No agent identity     │        │ • PKI verification      │             │
│  └─────────────────────────┘        └─────────────────────────┘             │
│                                                                              │
│  Status: ACTIVE                     Status: SCHEMA ONLY (Missing Engine)    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.4 Critical Vulnerabilities (from Security Audit)

| Vulnerability | CVSS | Status |
|---------------|------|--------|
| CORS Permissive | 5.3 | 🔴 Unfixed |
| SQL Injection (temporal) | 7.5 | 🔴 Unfixed |
| Path Traversal (export) | 6.5 | 🔴 Unfixed |
| Rate Limiting Stub | N/A | 🟡 Stub only |
| API Key in localStorage | N/A | 🟡 Vulnerable |

---

## 2. NotebookLM Prepper Analysis

### 2.1 Current Implementation

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                  NOTEBOOKLM PREPPER PIPELINE                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                   │
│  │   CORTEX DB  │───▶│  Synthesize  │───▶│  notebooklm/ │                   │
│  │  (SQLite)    │    │   Script     │    │  sources/    │                   │
│  └──────────────┘    └──────────────┘    └──────────────┘                   │
│         │                   │                     │                          │
│         ▼                   ▼                     ▼                          │
│    facts, entities      pandas              markdown files                   │
│    confidence           aggregation         per-project                      │
│                                                                              │
│  Script: scripts/synthesize_notebooklm.py                                    │
│  Output: notebooklm_sources/{project}_knowledge.md                          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Output Format

Each generated file follows this structure:

```markdown
# 🧠 CORTEX Domain: {PROJECT}

## 🔍 NOTAS DE INVESTIGACIÓN (CRÍTICO)
> NotebookLM: He detectado las siguientes lagunas en CORTEX para este proyecto.
- Hay **{N}** hechos sin verificar que requieren validación lógica.
- Las siguientes entidades carecen de conexiones relacionales: {entities}.

## Base de Conocimiento
### {fact_type}
- **{content}** (Confid: {confidence})
```

### 2.3 Current Coverage (from filesystem)

| Project | Facts Generated | Status |
|---------|-----------------|--------|
| cortex | ~30 facts | ✅ Active |
| moskv-swarm | ~50 facts | ✅ Active |
| naroa-web | ~15 facts | ✅ Active |
| __system__ | ~20 facts | ✅ Active |
| __bridges__ | ~10 facts | ✅ Active |

---

## 3. Contradictions Between Projects

### 3.1 Contradiction Matrix

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ARCHITECTURAL CONTRADICTIONS                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  C1: SECURITY vs USABILITY                                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ • CORS restrictive breaks Hive UI development                       │   │
│  │ • PKI signatures add friction to agent onboarding                   │   │
│  │ • Rate limiting may throttle legitimate swarm activity              │   │
│  │                                                                     │   │
│  │ RESOLUTION: Tiered security model                                   │   │
│  │ • Dev mode: permissive CORS, no sigs                                │   │
│  │ • Prod mode: strict CORS, PKI required                              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  C2: CONSENSUS V1 vs V2                                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ • V1 is simple but vulnerable to Sybil attacks                      │   │
│  │ • V2 is secure but computationally expensive                        │   │
│  │ • Migrating votes changes historical consensus scores               │   │
│  │                                                                     │   │
│  │ RESOLUTION: Dual-mode operation                                     │   │
│  │ • V1 for human agents (trusted environment)                         │   │
│  │ • V2 for AI agents (untrusted, requires reputation)                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  C3: SYNC DIRECTION                                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ • CORTEX wants to be Source of Truth                                │   │
│  │ • Legacy ~/.agent/memory/ files still used by external tools        │   │
│  │ • Bidirectional sync creates conflict resolution complexity         │   │
│  │                                                                     │   │
│  │ RESOLUTION: Gradual migration                                       │   │
│  │ • Phase 1: CORTEX → JSON (write-back)                               │   │
│  │ • Phase 2: JSON read-only, CORTEX write                             │   │
│  │ • Phase 3: Deprecate JSON entirely                                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  C4: TENANT ISOLATION vs CONSENSUS                                           │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ • Tenant isolation requires per-project facts                       │   │
│  │ • Consensus works best with cross-tenant visibility                 │   │
│  │ • Reputation is global but votes are per-fact                       │   │
│  │                                                                     │   │
│  │ RESOLUTION: Scoped consensus                                        │   │
│  │ • Facts: per-tenant isolated                                        │   │
│  │ • Reputation: global across tenants                                 │   │
│  │ • Trust edges: tenant-scoped                                        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  C5: IMMUTABILITY vs GRAPH EVOLUTION                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ • Transaction ledger is append-only (immutable)                     │   │
│  │ • Graph entities/relations need updates (mention_count++)           │   │
│  │ • Temporal facts can be deprecated (soft delete)                    │   │
│  │                                                                     │   │
│  │ RESOLUTION: Different immutability levels                           │   │
│  │ • Ledger: fully immutable                                           │   │
│  │ • Facts: soft-delete only                                           │   │
│  │ • Graph: mutable aggregates                                         │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Resolution Priorities

| Contradiction | Impact | Resolution Strategy |
|---------------|--------|---------------------|
| C1: Security vs Usability | High | Environment-based configuration |
| C3: Sync Direction | High | Deprecation timeline (3 months) |
| C2: V1 vs V2 Consensus | Medium | Dual-mode with clear boundaries |
| C4: Tenant vs Consensus | Medium | Global reputation, scoped votes |
| C5: Immutability vs Graph | Low | Accept different consistency models |

---

## 4. Wave 4 Roadmap

### 4.1 Phase Breakdown

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         WAVE 4 ROADMAP                                       │
│                    Sovereign AI Readiness                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  SPRINT 1-2: CRITICAL SECURITY (Weeks 1-4)                                  │
│  ═════════════════════════════════════════                                  │
│  □ Fix CORS configuration (cortex/api.py:80-86)                             │
│  □ Fix SQL injection in temporal filters (search.py:89)                     │
│  □ Fix path traversal in export (api.py:302-321)                            │
│  □ Implement rate limiting (Redis or in-memory)                             │
│  □ Add request validation middleware                                        │
│                                                                              │
│  DELIVERABLE: Security-hardened API ready for external exposure             │
│                                                                              │
│  SPRINT 3-4: RWC ENGINE (Weeks 5-8)                                         │
│  ═══════════════════════════════                                            │
│  □ Implement vote_v2() method in CortexEngine                               │
│  □ Fix VoteV2Request import in facts router                                 │
│  □ Implement reputation calculation with EMA                                │
│  □ Add temporal decay to votes                                              │
│  □ Create consensus_outcomes tracking                                       │
│  □ Add agent reputation update job                                          │
│                                                                              │
│  DELIVERABLE: Reputation-Weighted Consensus fully operational               │
│                                                                              │
│  SPRINT 5-6: SYNC CONSOLIDATION (Weeks 9-12)                                │
│  ═════════════════════════════════════════                                  │
│  □ Deprecate ~/.agent/memory/ write-back                                    │
│  □ Make CORTEX DB the exclusive Source of Truth                             │
│  □ Add migration tooling for legacy users                                   │
│  □ Update CLI to remove writeback commands                                  │
│  □ Add backup/restore functionality                                         │
│                                                                              │
│  DELIVERABLE: Single source of truth architecture                           │
│                                                                              │
│  SPRINT 7-8: NOTEBOOKLM ENHANCEMENT (Weeks 13-16)                           │
│  ═══════════════════════════════════════════════                            │
│  □ Add entity relationship graph to exports                                 │
│  □ Include consensus scores in NotebookLM output                            │
│  □ Add temporal snapshots ("what we knew at X time")                        │
│  □ Create NotebookLM feedback loop (verified facts back to CORTEX)          │
│  □ Add gap analysis automation                                              │
│                                                                              │
│  DELIVERABLE: Bidirectional NotebookLM integration                          │
│                                                                              │
│  SPRINT 9-10: TRUST GRAPH (Weeks 17-20)                                     │
│  ═══════════════════════════════════════                                    │
│  □ Implement trust_edges operations                                         │
│  □ Add EigenTrust-style transitive trust calculation                        │
│  □ Create trust delegation UI                                               │
│  □ Add collusion detection (clique analysis)                                │
│  □ Implement trust graph visualization                                      │
│                                                                              │
│  DELIVERABLE: Decentralized trust infrastructure                            │
│                                                                              │
│  SPRINT 11-12: SOVEREIGN AI POLISH (Weeks 21-24)                            │
│  ═══════════════════════════════════════════════                            │
│  □ Add cryptographic vote signatures (Ed25519)                              │
│  □ Implement staking mechanism (optional)                                   │
│  □ Create governance parameters (DAO-ready)                                 │
│  □ Add cross-swarm federation protocol                                      │
│  □ Performance optimization (caching, indexing)                             │
│                                                                              │
│  DELIVERABLE: Production-ready Sovereign AI memory                          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4.2 Detailed Implementation Plan

#### Sprint 1-2: Critical Security Fixes

```python
# cortex/api.py - CORS Fix
from cortex.config import ALLOWED_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # No more wildcard
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

# cortex/search.py - SQL Injection Fix
ALLOWED_TEMPORAL_FILTERS = {
    "active": "valid_until IS NULL",
    "deprecated": "valid_until IS NOT NULL",
}

def apply_temporal_filter(sql: str, filter_name: str) -> str:
    if filter_name not in ALLOWED_TEMPORAL_FILTERS:
        raise ValueError(f"Invalid temporal filter: {filter_name}")
    return sql + f" AND {ALLOWED_TEMPORAL_FILTERS[filter_name]}"
```

#### Sprint 3-4: RWC Engine Implementation

```python
# cortex/engine.py - Missing vote_v2 method

def vote_v2(
    self,
    fact_id: int,
    agent_id: str,
    value: int,
    reason: Optional[str] = None,
) -> float:
    """Cast a reputation-weighted vote (RWC v2)."""
    conn = self._get_conn()
    
    # 1. Get agent reputation
    row = conn.execute(
        "SELECT reputation_score FROM agents WHERE id = ? AND is_active = TRUE",
        (agent_id,)
    ).fetchone()
    if not row:
        raise ValueError(f"Agent {agent_id} not found or inactive")
    
    rep_score = row[0]
    vote_weight = rep_score  # Simplified - could include stake
    
    # 2. Insert/update vote
    conn.execute(
        """
        INSERT OR REPLACE INTO consensus_votes_v2 
        (fact_id, agent_id, vote, vote_weight, agent_rep_at_vote, created_at)
        VALUES (?, ?, ?, ?, ?, datetime('now'))
        """,
        (fact_id, agent_id, value, vote_weight, rep_score)
    )
    
    # 3. Recalculate with reputation weighting
    score = self._recalculate_consensus_v2(fact_id, conn)
    conn.commit()
    return score

def _recalculate_consensus_v2(self, fact_id: int, conn: sqlite3.Connection) -> float:
    """Calculate reputation-weighted consensus score."""
    row = conn.execute(
        """
        SELECT 
            SUM(v.vote * v.vote_weight * v.decay_factor) as weighted_sum,
            SUM(v.vote_weight * v.decay_factor) as total_weight
        FROM consensus_votes_v2 v
        JOIN agents a ON v.agent_id = a.id
        WHERE v.fact_id = ? AND a.is_active = TRUE
        """,
        (fact_id,)
    ).fetchone()
    
    weighted_sum = row[0] or 0
    total_weight = row[1] or 0
    
    if total_weight > 0:
        normalized = weighted_sum / total_weight  # [-1, 1]
        score = 1.0 + normalized  # [0, 2]
    else:
        score = 1.0
    
    # Update fact with new score
    confidence = self._determine_confidence_v2(score, total_weight)
    conn.execute(
        "UPDATE facts SET consensus_score = ?, confidence = ? WHERE id = ?",
        (score, confidence, fact_id)
    )
    
    return score
```

### 4.3 Success Metrics

| Phase | Metric | Target |
|-------|--------|--------|
| Security | Vulnerabilities (CVSS > 5) | 0 |
| RWC | Test coverage | > 90% |
| Sync | Legacy write-back usage | 0% |
| NotebookLM | Facts exported | 100% coverage |
| Trust Graph | Trust edges created | > 100 |
| Performance | API p99 latency | < 100ms |

---

## 5. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Security fixes break existing clients | Medium | High | Gradual rollout with feature flags |
| RWC migration corrupts consensus scores | Low | Critical | Backup before migration, idempotent ops |
| NotebookLM format changes break ingestion | Medium | Medium | Versioned output formats |
| Trust graph creates reputation cartels | Medium | Medium | Collusion detection, diversity requirements |
| Performance degradation with RWC | Medium | Medium | Caching, materialized views |

---

## 6. Conclusion

CORTEX V4.0 has a solid foundation with:
- ✅ Complete schema for RWC
- ✅ Base consensus layer operational
- ✅ Tenant isolation working
- ✅ Graph memory functional
- ✅ NotebookLM prepper generating exports

**Critical gaps before Sovereign AI readiness:**
1. 🔴 Security vulnerabilities must be fixed
2. 🔴 RWC engine needs implementation
3. 🟡 Sync architecture needs consolidation
4. 🟡 Trust graph needs completion

**Recommendation:** Proceed with Wave 4 as outlined, prioritizing security fixes in Sprint 1-2 to enable safe external exposure.

---

*Generated by Kimi Code CLI | CORTEX V4.0 Strategic Analysis*
