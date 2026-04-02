# Awesome List PR Template

## For adding CORTEX-Persist to awesome lists

### PR Title
```
Add CORTEX-Persist — tamper-evident memory for AI agents
```

### PR Body

```markdown
## What is CORTEX-Persist?

[CORTEX-Persist](https://github.com/borjamoskv/Cortex-Persist) is a local-first, tamper-evident memory and trust layer for AI agents.

It provides:
- **Append-only ledger** for facts, decisions, and state transitions
- **SHA-256 hash chaining** across all stored entries
- **Merkle checkpoints** for batch integrity verification
- **Deterministic audit exports** (JSON audit packs)
- **Python SDK** with async support

### Why it fits this list

<!-- Customize this section per list -->
CORTEX-Persist solves a growing problem in AI agent infrastructure: **proving what an agent knew, when it knew it, and what it did next**. As autonomous agents make critical decisions (financial transactions, legal actions, infrastructure changes), having cryptographic proof of their decision context becomes essential.

### Quality checklist

- [x] Open source (Apache 2.0)
- [x] Published on PyPI (`pip install cortex-persist`)
- [x] CI/CD with GitHub Actions
- [x] >80% code coverage (Codecov)
- [x] Comprehensive documentation (MkDocs)
- [x] CONTRIBUTING.md, CODE_OF_CONDUCT.md, SECURITY.md
- [x] Multi-language README (English, Spanish, Chinese)
- [x] Active development (regular commits)
```

### Issue Template (for lists that prefer issues first)

```markdown
**Title:** Suggestion: CORTEX-Persist — tamper-evident memory for AI agents

**Body:**
Hi! I'd like to suggest adding [CORTEX-Persist](https://github.com/borjamoskv/Cortex-Persist) to this list.

It's a local-first memory layer that makes AI agent decisions tamper-evident using SHA-256 hash chains and Merkle proofs. Useful for compliance, forensics, and multi-agent trust.

- Apache 2.0 licensed
- Published on PyPI
- Active CI/CD and >80% coverage

Happy to submit a PR if you think it's a good fit. Thanks!
```
