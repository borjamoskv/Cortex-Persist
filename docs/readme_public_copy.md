# CORTEX-Persist

**Tamper-evident memory and decision lineage for autonomous systems.**

## The Problem
Agents can act. They cannot remember. Current AI systems excel at generation but fail at continuity. They produce plausible output—but lack durable, operational memory. Without a verification substrate, autonomous systems drift, hallucinate context, and leave no audit trail.

Right now, your agents don't have memory. They have disjointed logs, context windows, and optimism.

## The Solution
CORTEX-Persist is the trust layer for autonomous execution. A local-first memory and verification substrate built so your AI can remember, retrieve, and cryptographically prove what happened in a long-running execution. 

- **Store with intent**: Capture decisions, operational states, and errors as typed memory.
- **Verify with cryptography**: Anchor every state change to a tamper-evident ledger.
- **Retrieve with precision**: Hybrid semantic & lexical search bounded by cryptographic confidence.

## Features
- **Tamper-Evident Ledger**: Cryptographic lineage for memory operations (hash chaining).
- **Hybrid Retrieval**: Combine vector (sqlite-vec) and lexical search.
- **Memory Governance**: Promote, compact, decay, or archive semantic memory.
- **Autonomous Ready**: Built for tool-using agents, long-running workflows, and compliance audits.

## Quickstart

```bash
pip install "cortex-persist[all]"
```

Initialize the Ledger:
```bash
cortex verify-ledger
```

Store an auditable memory:
```bash
cortex store "Vendor X failed compliance check" \
  --type decision \
  --project procurement \
  --confidence C4 \
  --source agent:reviewer
```

Retrieve context:
```bash
cortex search "compliance vendor failure"
```

## Doctrine 
CORTEX strictly enforces the **Sovereign Axioms**:
1. **No Hidden Entropy:** If an operation is not in the ledger, it never happened.
2. **Deterministic Time-Travel:** Rollbacks map perfectly to exact states.
3. **Byzantine Validation:** A generative output must face a deterministic validation boundary before being committed as a fact.

For more on the CORTEX Philosophy and Exergy principles, see `ARCHITECTURE.md`.

## License
Apache 2.0
