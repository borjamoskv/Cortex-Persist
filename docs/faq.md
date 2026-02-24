# FAQ

Common questions about CORTEX, answered honestly.

---

## General

### Is CORTEX production-ready?

**Not yet.** CORTEX is in **v8.0 alpha**. The architecture is solid and tests pass, but there are known issues being actively resolved (singleton thread-safety, persistent audit logging). We recommend CORTEX for:

- ✅ Development and prototyping
- ✅ Compliance proof-of-concepts
- ✅ Pre-production evaluation
- ⚠️ Production — only with awareness of alpha status

See the [Changelog](changelog.md) for current progress.

### Why should I use CORTEX instead of just logging?

Traditional logging captures *what happened*. CORTEX proves *it wasn't tampered with*. Key differences:

| Feature | Logging | CORTEX |
|:---|:---|:---|
| Tamper detection | ❌ | ✅ SHA-256 hash chain |
| Integrity verification | ❌ | ✅ Merkle checkpoints |
| Multi-agent consensus | ❌ | ✅ WBFT voting |
| Compliance reports | ❌ | ✅ EU AI Act Art. 12 |
| Semantic search over history | ❌ | ✅ Vector + graph |

### Who built this?

[Borja Moskv](https://github.com/borjamoskv) — solo developer, based in Bilbao. CORTEX is 103 commits in 9 days (as of Feb 24, 2026). This is a real product, not a weekend experiment.

---

## Licensing

### Why BSL 1.1 and not Apache 2.0?

The **Business Source License 1.1** is the same license used by [CockroachDB](https://github.com/cockroachdb/cockroach), [Sentry](https://github.com/getsentry/sentry), and [MariaDB](https://mariadb.com/bsl-faq-mariadb/). It works like this:

- ✅ **Free for development, testing, and non-production use**
- ✅ **Free for internal tools** (not offered as a service to third parties)
- ✅ **Automatically converts to Apache 2.0 in 2030**
- ❌ You cannot resell CORTEX as a hosted service without a commercial license

This protects the project while keeping it effectively open-source for 99% of users.

### Can I use CORTEX in my company?

Yes. BSL 1.1 allows all internal use. You only need a commercial license if you're offering CORTEX to third parties as a service (e.g., "Trust-as-a-Service" built on CORTEX).

---

## Comparison with Alternatives

### How does CORTEX compare to Mem0?

**They're complementary, not competing.** Mem0 is an excellent memory layer for AI agents ($249/mo for cloud). CORTEX sits *on top* of Mem0 (or Zep, or Letta) and adds:

- Cryptographic proof that memories weren't tampered with
- EU AI Act compliance reports
- Multi-agent consensus verification

Think of it as: **Mem0 = the memory. CORTEX = the notary.**

### How does CORTEX compare to Zep?

Zep focuses on knowledge graphs and memory enrichment. CORTEX focuses on trust verification and compliance. Use Zep for better recall, use CORTEX for provable integrity.

### Why not use blockchain for immutability?

Blockchain adds network overhead, transaction costs, and complexity. CORTEX achieves the same tamper-detection guarantees with:

- Hash-chained ledger (same principle, no network)
- Merkle tree checkpoints (efficient batch verification)
- Local-first storage (zero latency)

No gas fees. No consensus delays. Same cryptographic guarantees.

---

## Technical

### What databases does CORTEX support?

| Layer | Local | Cloud |
|:---|:---|:---|
| L1 (Working Memory) | In-memory | Redis |
| L2 (Vector Memory) | sqlite-vec | Qdrant |
| L3 (Episodic Ledger) | SQLite (WAL) | AlloyDB / PostgreSQL |

### Does CORTEX work offline?

Yes. CORTEX is **local-first** by default. Everything runs on SQLite — no network required. Cloud features (Redis, Qdrant, AlloyDB) are optional for enterprise scale.

### What's the MCP Server?

The [Model Context Protocol](https://modelcontextprotocol.io/) is an open standard for connecting AI agents to tools. CORTEX's MCP server makes it a plug-in for:

- Claude Code
- Cursor
- Windsurf
- Antigravity
- Any MCP-compatible IDE

```bash
python -m cortex.mcp
```

### How do I report a security issue?

See [SECURITY.md](https://github.com/borjamoskv/cortex/blob/master/SECURITY.md) for responsible disclosure instructions. Do not open public GitHub issues for security vulnerabilities.
