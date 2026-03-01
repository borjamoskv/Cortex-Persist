# CORTEX Launch Kit — Distribution Copy

> All launch assets in one file. Copy-paste ready for each platform.

---

## 1. Product Hunt

### Tagline (60 chars)
```
Trust infrastructure for autonomous AI — like SSL, but for agents
```

### Description (260 chars)
```
CORTEX adds SHA-256 hash chains, Merkle checkpoints, and Byzantine consensus to your AI agent's memory. Local-first, free, and EU AI Act compliant out of the box. Works with Mem0, Zep, LangChain, CrewAI. pip install cortex-memory.
```

### First Comment (Hunter's Narrative)

```
Hey PH! 👋

I'm Borja, and I built CORTEX because I realized something terrifying: AI agents are making millions of decisions per day, and nobody can prove those decisions weren't tampered with.

Mem0 stores what agents remember. Zep builds knowledge graphs. Letta manages state. But none of them can answer: "Can you cryptographically prove this decision is authentic?"

CORTEX is a trust layer that sits ON TOP of your existing memory system and adds:

🔗 SHA-256 hash-chained immutable ledger (tamper = detected)
🌳 Merkle tree checkpoints for O(log n) batch verification
🤝 Byzantine fault-tolerant consensus for multi-agent systems
🔐 Privacy Shield with 11 secret detection patterns
📋 One-command EU AI Act compliance reports

The EU AI Act (Article 12, enforced August 2026) mandates tamper-proof logging and full traceability for AI systems. Fines are up to €30M or 6% of global revenue. CORTEX gives you compliance in 30 seconds:

pip install cortex-memory
cortex compliance-report
✅ Score: 5/5

It's free (Apache 2.0), local-first (no cloud required), and has 1,500+ tests across 67K+ lines of production code.

I'd love your feedback — especially if you're building with AI agents and worry about trust, compliance, or audit trails.

— Borja
```

### Topics
```
Artificial Intelligence, Developer Tools, Open Source, Security, Compliance
```

---

## 2. Hacker News — Show HN

### Title
```
Show HN: CORTEX – SHA-256 hash-chained trust layer for AI agent memory (Apache 2.0)
```

### Text Body
```
I've been building CORTEX for the past year to solve a specific problem: AI agents make decisions, but there's no cryptographic proof those decisions are authentic or untampered.

CORTEX is a trust layer that sits on top of existing memory systems (Mem0, Zep, custom stores) and adds:

- SHA-256 hash-chained immutable ledger — every fact is chained to the previous one. Tamper with one record and the chain breaks.
- Merkle tree checkpoints — periodic batch verification with O(log n) proof generation.
- WBFT consensus — reputation-weighted Byzantine fault-tolerant verification for multi-agent setups. Tolerates up to 1/3 malicious agents.
- Privacy Shield — 11-pattern secret detection that blocks API keys, tokens, and PII before they hit the database.
- EU AI Act compliance — one-command report generation for Article 12 requirements (enforced August 2026, fines up to €30M).

Architecture highlights:
- Local-first: SQLite + sqlite-vec for embeddings. No cloud required.
- MCP native: works with Claude Code, Cursor, Windsurf via `python -m cortex.mcp`
- 1,500+ test functions, 67K+ LOC, Python 3.10+

Quick start:

    pip install cortex-memory
    cortex store --type decision --project my-agent "Chose OAuth2 PKCE for auth"
    cortex verify 42
    # → ✅ VERIFIED — Hash chain intact, Merkle sealed

I'm not trying to replace Mem0 or Zep — I'm trying to make whatever memory layer you use provably trustworthy. Think of it as what SSL/TLS did for HTTP, but for agent memory.

Source: https://github.com/borjamoskv/cortex
Docs: https://cortexpersist.dev
Install: pip install cortex-memory

Happy to answer any questions about the cryptography, the consensus protocol, or the architecture.
```

---

## 3. Twitter/X Launch Thread

### Tweet 1 — Hook
```
AI agents make millions of decisions per day.

Can you prove a single one wasn't tampered with?

Today I'm open-sourcing CORTEX — SHA-256 hash-chained trust infrastructure for AI memory.

🧵 Thread:
```

### Tweet 2 — The Problem
```
The problem with AI memory today:

• Mem0 stores memories → but no tamper proof
• Zep builds graphs → but no audit trail
• Letta manages state → but no compliance

Your agent remembers… but can you VERIFY what it remembers?
```

### Tweet 3 — The Solution
```
CORTEX sits ON TOP of your existing memory layer and adds:

🔗 SHA-256 hash-chained ledger
🌳 Merkle tree checkpoints
🤝 Byzantine consensus (multi-agent)
🔐 Privacy Shield (11 patterns)
📋 EU AI Act compliance reports

Think SSL/TLS, but for agents.
```

### Tweet 4 — Demo
```
30 seconds to trust:

pip install cortex-memory

cortex store --type decision "Chose PKCE for auth"
cortex verify 42
✅ VERIFIED — Hash chain intact

cortex compliance-report
✅ 5/5 — Article 12 compliant

That's it. Your AI is now auditable.
```

### Tweet 5 — EU AI Act Urgency
```
EU AI Act, Article 12 (August 2026):

✅ Automatic logging of all agent decisions
✅ Tamper-proof storage
✅ Full traceability
✅ Periodic verification

Fines: up to €30M or 6% of global revenue.

CORTEX gives you compliance in one command.
```

### Tweet 6 — Comparison
```
How CORTEX compares:

                 CORTEX  Mem0   Zep   Letta
Crypto Ledger    ✅      ❌    ❌    ❌
Merkle Trees     ✅      ❌    ❌    ❌
BFT Consensus    ✅      ❌    ❌    ❌
Privacy Shield   ✅      ❌    ❌    ❌
Local-First      ✅      ❌    ❌    ✅
EU AI Act        ✅      ❌    ❌    ❌
Cost             Free    $249  $$$   Free
```

### Tweet 7 — Architecture
```
Under the hood:

• SQLite + sqlite-vec (local, no cloud)
• MCP native (Claude Code, Cursor, Windsurf)
• Multi-tenant ready
• 1,500+ tests, 67K+ LOC
• Python 3.10+
• Apache 2.0

Built for production from day 1.
```

### Tweet 8 — MCP Integration
```
Best part: it's an MCP server.

One command:
python -m cortex.mcp

Now every AI decision in your IDE is:
✅ Hash-chained
✅ Merkle-sealed
✅ Compliance-ready

Works with Claude Code, Cursor, Windsurf, Antigravity.
```

### Tweet 9 — Philosophy
```
Mem0 stores data about conversations.
CORTEX stores facts about cognition.

That's the difference between a database and a mind.

One is infrastructure. The other is trust.
```

### Tweet 10 — CTA
```
CORTEX is free, open source, and production-ready.

⭐ Star: github.com/borjamoskv/cortex
📦 Install: pip install cortex-memory
📚 Docs: cortexpersist.dev

If you're building AI agents and care about trust, compliance, or audit trails — try it.

Your agents deserve provable integrity.
```

---

## 4. LinkedIn Post

```
I'm publicly launching CORTEX today — open-source trust infrastructure for AI agent memory.

Here's the uncomfortable question nobody in the AI industry is answering:

AI agents are making millions of decisions per day across every industry. Finance, healthcare, legal, insurance. But can you cryptographically prove those decisions are authentic? That the memory wasn't tampered with? That your agent's reasoning chain is intact?

The EU AI Act (Article 12, enforced August 2026) now requires exactly this: tamper-proof logging, full traceability, and periodic integrity verification. Fines up to €30M or 6% of global revenue.

CORTEX is my answer. It's a trust layer that sits on top of existing AI memory systems (Mem0, Zep, Letta, or custom) and adds:

• SHA-256 hash-chained immutable ledger
• Merkle tree cryptographic checkpoints
• Byzantine fault-tolerant multi-agent consensus
• Privacy Shield with 11 secret detection patterns
• One-command EU AI Act compliance reports

It's local-first (no cloud required), free (Apache 2.0), and has 1,500+ tests across 67K+ lines of production code.

Think of it as what SSL/TLS did for web communications, but for AI agent memory.

If you're building AI products and your compliance team hasn't asked "can you prove our AI's decisions are untampered?" — they will soon.

🔗 GitHub: github.com/borjamoskv/cortex
📦 Install: pip install cortex-memory
📚 Docs: cortexpersist.dev

Happy to demo it for any team evaluating AI compliance tooling.

#AI #AIAgents #Compliance #EUAIAct #OpenSource #TrustInfrastructure #AIMemory
```

---

## 5. Enterprise Cold Outreach Email

### Subject Line Options
```
A) Your AI agents can't prove their own decisions yet
B) EU AI Act compliance for your agent pipeline — 30 seconds
C) We built the SSL/TLS of AI agent memory (open source)
```

### Email Body
```
Hi {{FIRST_NAME}},

I noticed {{COMPANY}} is building with {{FRAMEWORK: LangChain/CrewAI/AutoGen}}. Quick question: can you cryptographically prove that your agents' decisions haven't been tampered with?

The EU AI Act (Article 12, August 2026) now requires:
— Tamper-proof logging of all AI decisions
— Full traceability and explainability
— Periodic integrity verification
Fines: up to €30M or 6% of global revenue.

I built CORTEX specifically to solve this. It's a trust layer that sits ON TOP of your existing memory system and adds SHA-256 hash chains, Merkle checkpoints, and Byzantine consensus.

30 seconds to compliance:

  pip install cortex-memory
  cortex compliance-report
  ✅ Score: 5/5 — Article 12 compliant

It's free and open source (Apache 2.0), with 1,500+ tests and 67K+ lines of production code. No cloud required.

Would you be open to a 15-minute call this week to see if CORTEX fits your compliance roadmap?

Best,
Borja Moskv
Creator, CORTEX
github.com/borjamoskv/cortex
```

### Follow-Up (Day 3)
```
Hi {{FIRST_NAME}},

Just following up on my note about AI agent compliance.

The simplest way to evaluate: run `pip install cortex-memory && cortex compliance-report` on any machine with your agent logs. Takes 30 seconds. If the score isn't 5/5, CORTEX can fix that.

Happy to demo live if you'd prefer.

— Borja
```

---

## 6. Target Companies for Outreach (Top 20)

| Company | Why | Framework | Contact Role |
|:---|:---|:---|:---|
| Anthropic customers | Building AI agents daily | Custom | Head of Eng |
| Langbase | LangChain ecosystem | LangChain | CTO |
| CrewAI | Multi-agent framework | CrewAI | Founder |
| AutoGen Studio | Microsoft agent framework | AutoGen | Lead Dev |
| Fixie.ai | Agent platform | Custom | VP Eng |
| Relevance AI | No-code AI agents | Custom | CTO |
| Dust.tt | Enterprise AI assistants | Custom | CTO |
| Voiceflow | Conversational AI | Custom | Head of Platform |
| Cognosys | AI agent startup | Custom | CTO |
| Sierra.ai | Enterprise AI agents | Custom | VP Eng |
| Adept AI | Agent-first company | Custom | Staff Eng |
| Cohere | Enterprise LLM | Custom | Head of Solutions |
| Writer.com | Enterprise AI | Custom | CTO |
| Jasper AI | Content AI | Custom | VP Eng |
| Copy.ai | GTM AI platform | Custom | CTO |
| Moveworks | IT AI agents | Custom | VP Platform |
| Intercom Fin | Support AI | Custom | Head of AI |
| Salesforce Agentforce | Enterprise agents | Custom | Platform Lead |
| ServiceNow Now Assist | IT AI agents | Custom | VP AI Platform |
| Klarna AI | Fintech AI | Custom | Head of Engineering |

---

## Launch Calendar

| Day | Action | Platform |
|:---|:---|:---|
| D-1 | Schedule all tweets in Twitter composer | Twitter/X |
| D+0 | Submit to Product Hunt (12:01 AM PT) | Product Hunt |
| D+0 | Post Show HN (10 AM ET) | Hacker News |
| D+0 | Post LinkedIn article | LinkedIn |
| D+0 | Tweet thread (stagger 15 min between) | Twitter/X |
| D+1 | Send first 10 cold emails | Email |
| D+3 | Follow-up emails | Email |
| D+7 | Post recap thread with early metrics | Twitter/X |
