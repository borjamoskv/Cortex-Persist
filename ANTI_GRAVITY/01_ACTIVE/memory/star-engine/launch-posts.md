<!-- [C5-REAL] Exergy-Maximized -->
# 🚀 Launch Posts — CORTEX-Persist

> **Timing:** Tuesday–Thursday, 9:00 AM PST (17:00 CET)
> **Strategy:** Post on HN + Reddit within the same 4-hour window for momentum

---

## 1. Hacker News (Show HN)

### Title
```
Show HN: CORTEX-Persist – Tamper-evident memory for AI agents (SHA-256 chains)
```

### First Comment
```
Hey HN,

I built CORTEX-Persist because I got tired of the "trust me bro" approach to AI agent memory.

The problem: When an autonomous agent makes a critical decision — executing a trade, sending an email, modifying infrastructure — you need to prove what context it had at that moment. Logs get mutated. Databases get edited. There's no cryptographic proof that the record wasn't altered after the fact.

CORTEX sits between your agent runtime and your memory layer. Every fact and decision gets:
- SHA-256 hashed and chained to the previous entry
- Periodically sealed into Merkle checkpoints
- Exportable as deterministic audit packs (JSON)

If anyone edits a record after the fact, the hash chain breaks and verification fails.

It's NOT a vector database replacement (use Qdrant/Pinecone for RAG). It's NOT an observability platform (use Datadog for metrics). It's specifically the trust/integrity layer that sits alongside those tools.

Local-first by default (SQLite + WAL), multi-tenant API for teams, and a Python SDK:

    pip install cortex-persist

Would love feedback on the cryptographic model and the threat model doc: https://github.com/borjamoskv/Cortex-Persist/blob/main/docs/SECURITY_TRUST_MODEL.md

GitHub: https://github.com/borjamoskv/Cortex-Persist
```

---

## 2. Reddit

### r/Python

**Title:** `I built a tamper-evident memory layer for AI agents in Python`

**Body:**
```
CORTEX-Persist is an open-source Python library that makes AI agent decisions tamper-evident.

Every memory write gets SHA-256 hashed and chained. If anyone edits the database record after the fact, verification fails mathematically. Think "git for agent cognition" but with cryptographic integrity guarantees.

Quick example:

    from cortex import CortexEngine

    engine = CortexEngine()
    receipt = await engine.store_fact(
        content="User approved transaction $5,000",
        fact_type="decision",
        project="fin-fraud-bot",
    )
    assert await engine.verify(receipt.hash) is True

Use cases:
- Proving what context an agent had when making irreversible decisions
- Multi-agent state propagation tracing
- Compliance audit trails for regulated industries
- Post-incident forensics (detecting silent data mutation)

pip install cortex-persist

GitHub: https://github.com/borjamoskv/Cortex-Persist

Apache 2.0 | Python 3.10+ | Full test suite with Codecov | MkDocs documentation

Would love feedback from the Python community!
```

### r/MachineLearning

**Title:** `[P] CORTEX-Persist: Cryptographic decision lineage for autonomous AI agents`

**Body:**
```
As AI agents become more autonomous and make higher-stakes decisions, there's a growing need for provable decision lineage — not just logging what happened, but mathematically proving what an agent knew at decision time.

CORTEX-Persist is an open-source trust layer that:
- Hash-chains every fact/decision with SHA-256
- Creates Merkle checkpoints for batch verification
- Detects any post-hoc data manipulation
- Exports deterministic audit packs

It's designed for production agent systems where you need to answer: "What exactly did the agent know when it made this decision, and can I prove the record hasn't been altered?"

Not a replacement for vector DBs or observability — it's the integrity layer that sits alongside them.

Paper/docs on the cryptographic model: [link]
GitHub: https://github.com/borjamoskv/Cortex-Persist
```

### r/artificial

**Title:** `Open-source: Tamper-proof memory for AI agents — prove what your LLM knew`

---

## 3. Twitter/X Thread

```
🧵 I built tamper-evident memory for AI agents.

Here's why "just use logs" isn't enough when agents make irreversible decisions: 👇

1/ The problem:
Your AI agent executes a $50k trade.
The client asks: "What data did the agent have when it decided?"
You check the logs... but someone edited the database yesterday.

How do you prove the record is the ORIGINAL?

You can't. That's the problem.

2/ CORTEX-Persist solves this:
Every memory write → SHA-256 hashed → chained to previous entry.

Edit a record? Hash chain breaks. Verification fails.

No wiggle room. Math doesn't lie.

3/ It's NOT:
❌ A vector database (use Qdrant for RAG)
❌ An observability platform (use Datadog for metrics)
❌ A blockchain (no consensus needed)

It IS:
✅ A trust layer between your agent and its memory
✅ Local-first (SQLite)
✅ Python-native

4/ The 30-second demo:

pip install cortex-persist
cortex init
cortex memory store --agent "risk-bot" --content "Transaction flagged"
cortex verify ledger
# ✔ VERIFIED: Hash chain intact

# Now try tampering...
sqlite3 cortex.db "UPDATE facts SET content='Approved'"
cortex verify ledger
# ✘ TAMPER DETECTED

5/ Use cases:
• Autonomous trading bots → prove decision context
• Legal AI → defensible audit trails
• Multi-agent systems → trace state propagation
• Compliance → exportable audit packs

Open source. Apache 2.0.

GitHub: github.com/borjamoskv/Cortex-Persist

⭐ if you think AI agents need accountability, not just vibes.
```

---

## 4. Dev.to Article

### Title
```
How I Built Tamper-Evident Memory for AI Agents (and Why Logs Aren't Enough)
```

### Tags
`ai`, `python`, `security`, `opensource`

### Outline
1. **The Problem** — AI agents make decisions, but we can't prove what they knew
2. **Why Logs Fail** — Mutable databases, no integrity guarantees
3. **The Architecture** — SHA-256 chains, Merkle trees, append-only ledger
4. **Code Walkthrough** — Python SDK, 5-minute quickstart
5. **Real-World Use Cases** — Trading, legal, compliance
6. **What's Next** — Multi-tenant, cloud-ready scaling
7. **CTA** — Star on GitHub, try it, give feedback

---

## 5. LinkedIn Post

```
I've been working on a problem that will become critical as AI agents mature:

How do you PROVE what an AI agent knew when it made a decision?

Not "I think the logs say..." but mathematically provable proof that the record hasn't been altered.

I built CORTEX-Persist — an open-source Python library that creates tamper-evident memory for AI systems:

🔐 SHA-256 hash chains on every memory write
📋 Merkle proofs for batch verification
📦 Exportable audit packs for compliance
🔍 Instant tamper detection

As autonomous agents enter finance, legal, and healthcare, the question won't be "what did the AI do?" — it will be "can you prove it?"

If you're building AI agent infrastructure, I'd love your feedback:
https://github.com/borjamoskv/Cortex-Persist

#AI #OpenSource #Python #AIAgents #Compliance #Security
```

---

## Post-Launch Monitoring

After posting, track:
- [ ] HN upvotes + position (target: front page = 30+ points)
- [ ] Reddit karma on each post
- [ ] Twitter impressions + retweets
- [ ] GitHub star count (check star-history.com)
- [ ] PyPI download spikes
- [ ] New GitHub issues/discussions from launch traffic
