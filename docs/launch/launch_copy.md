# CORTEX — Launch Copy

> **Optimal publish window: Monday–Tuesday, 14:00–16:00 UTC**

---

## Hacker News — "Show HN"

**Title:**
```
Show HN: CORTEX – Cryptographic memory verification for AI agents (Apache 2.0, local-first)
```

**Body:**
```
I built CORTEX after realizing that every AI agent framework focuses on
WHAT agents remember — but nobody has solved HOW you verify those memories
are correct, unmodified, and auditable.

The EU AI Act (Article 12, enforced August 2026) requires:
  - Tamper-proof logging of all AI decisions
  - Full traceability and explainability
  - Periodic integrity verification
  - Fines: up to €30M or 6% global revenue

CORTEX addresses this by adding a cryptographic trust layer ON TOP of
your existing memory stack. It doesn't replace Mem0/Zep/Letta —
it certifies them.

HOW IT WORKS:
  - SHA-256 hash-chained immutable ledger (every fact verifiable)
  - Merkle tree checkpoints (batch integrity, tamper-evident)
  - WBFT consensus (multi-agent Byzantine fault tolerance)
  - Privacy Shield (11-pattern secret detection before any INSERT)
  - AST Sandbox (safe LLM-generated code execution)
  - Local-first (SQLite, zero cloud dependency)
  - MCP Server native (Claude Code, Cursor, Windsurf)

THE ANALOGY:
  CORTEX is to AI memory what SSL/TLS is to web communications.
  You wouldn't run a web server without TLS in 2026.
  Why run an AI agent without memory verification?

QUICK START:
  pip install cortex-memory

  from cortex import CortexEngine
  engine = CortexEngine()
  await engine.store_fact("Approved loan #443", fact_type="decision", project="fintech-agent")
  # → SHA-256 chained, Merkle-sealed, Privacy-shielded, auditable

VERIFY ANY FACT:
  cortex verify 42
  # → ✅ VERIFIED — Hash chain intact, Merkle sealed

NUMBERS:
  - 45,500+ production LOC
  - 1,162+ tests
  - 55+ REST endpoints
  - 444 modules
  - Apache 2.0. Free.

GitHub: https://github.com/borjamoskv/cortex
Docs:   https://cortexpersist.dev

Happy to answer questions about the cryptographic design,
the WBFT consensus protocol, or the EU AI Act compliance angle.
```

---

## Reddit — r/LocalLLaMA

**Title:**
```
I built a cryptographic memory layer for AI agents (EU AI Act compliant, Apache 2.0, local-first)
```

**Body:**
```
TL;DR: CORTEX adds SHA-256 ledger + Merkle checkpoints + Byzantine consensus
to AI agent memory. Think "SSL/TLS but for agent decisions". Free, local-first, MCP-native.

---

The problem I kept hitting while building AI agents:

Every agent framework tells you HOW to store memory but NOBODY answers:
  "How do you PROVE that memory wasn't modified?"
  "Can you generate a compliance audit trail for regulators?"
  "What happens when two agents agree on conflicting memories?"

So I built CORTEX.

WHAT IT IS:
CORTEX sits between your agent and its memory layer as a cryptographic
verification engine. It doesn't replace Mem0, Zep, LangChain memory,
or SQLite — it wraps them in a trust layer.

THE STACK (all open source, local-first):
  ├── SHA-256 hash-chained ledger    ← every fact immutable + verifiable
  ├── Merkle tree checkpoints        ← tamper-evident batch verification
  ├── WBFT consensus                 ← multi-agent Byzantine fault tolerance
  ├── Privacy Shield (11 patterns)   ← secrets never hit the DB
  ├── AST Sandbox                    ← safe code execution
  ├── Tripartite memory              ← Redis (hot) → Qdrant → Ledger
  └── MCP Server native              ← Claude Code, Cursor, Windsurf plug in directly

3-LINE SETUP:
  pip install cortex-memory

  from cortex import CortexEngine
  engine = CortexEngine()
  await engine.store_fact("content", fact_type="decision", project="my-agent")

VERIFY ANY FACT:
  cortex verify 42
  # → ✅ VERIFIED — Hash chain intact, Merkle sealed

Why this matters NOW:
EU AI Act Article 12 goes live August 2026.
Penalty: €30M or 6% global revenue for non-compliant AI systems.
Enterprise clients are already asking their AI vendors for compliance docs.
CORTEX generates those reports in one command.

Happy to geek out on:
- The WBFT consensus implementation (reputation-weighted voting)
- Why Merkle trees beat blockchain for low-latency agent use cases
- The Privacy Shield secret-detection pipeline

GitHub: https://github.com/borjamoskv/cortex
Apache 2.0. 45K+ LOC. 1,162+ tests.
```

---

## Twitter/X — Thread

```
Tweet 1:
AI agents make millions of decisions per day.

But can you PROVE any of them are correct?

We built CORTEX — cryptographic memory verification for AI agents.
Think SSL/TLS, but for agent decisions. 🧵

Tweet 2:
The problem isn't storing what agents remember.
That's solved (Mem0, Zep, Letta are great for that).

The problem is VERIFYING that memory is:
→ Unmodified
→ Auditable
→ Traceable to the original decision

Tweet 3:
CORTEX adds a trust layer on top of your existing stack:

├── SHA-256 hash-chained ledger
├── Merkle tree checkpoints
├── WBFT consensus (multi-agent)
├── Privacy Shield (11 patterns)
└── AST Sandbox (safe code exec)

Local-first. MCP-native. Apache 2.0. Free.

Tweet 4:
EU AI Act Art.12 — August 2026.
Fines: €30M or 6% global revenue.

Requires: tamper-proof decision logs, full traceability, integrity verification.

CORTEX generates the compliance report in one command.

Tweet 5:
pip install cortex-memory

from cortex import CortexEngine
engine = CortexEngine()
await engine.store_fact("Decision", fact_type="decision", project="agent")

cortex verify 42
→ ✅ SHA-256 intact, Merkle sealed. 3ms.

GitHub: github.com/borjamoskv/cortex
```

---

## LinkedIn — Executive angle

```
AI agents are making thousands of decisions inside your business every day.

Here's the question no one is asking yet: can you PROVE those decisions were correct?

Not "probably correct." Not "the model said so." Provably, cryptographically, auditably correct.

The EU AI Act (Article 12, enforcement August 2026) will make this mandatory for regulated industries. Penalty for non-compliance: up to €30 million.

We built CORTEX to solve this — a cryptographic trust layer for AI agent memory that works on top of whatever stack you already use. No migration. No cloud dependency. Apache 2.0.

CORTEX is to AI memory what SSL/TLS is to web communications.

You didn't build your own encryption layer. You installed TLS.
You don't need to build your own audit trail. → pip install cortex-memory

https://cortexpersist.dev
```

---

## GitHub — Pinned issue (for contributors)

**Title:** `[RFC] WBFT consensus: does it scale beyond 50 nodes?`

**Body:**
```
The WBFT implementation uses reputation-weighted Bayesian scoring to reject
nodes with score < 0.6 without a central coordinator.

I believe it scales to 50+ nodes. I might be wrong.

If you want to audit the claim: cortex/consensus/wbft.py line 147.

This issue is for anyone who wants to challenge the design, propose
improvements, or benchmark it at scale. All data welcome.
```

---

*Last updated: 2026-02-24*
