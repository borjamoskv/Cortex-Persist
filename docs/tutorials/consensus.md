# Tutorial: Multi-Agent Consensus (WBFT)

Use CORTEX's Weighted Byzantine Fault Tolerant consensus to have multiple AI agents vote on facts, building collective confidence.

## The Problem

When multiple AI agents collaborate — in a LangChain chain, CrewAI crew, or AutoGen swarm — they may disagree. Agent A says "chose PostgreSQL", Agent B says "chose MySQL". Which decision is the truth?

Traditional systems pick the last write. CORTEX lets agents **vote**, weighting each vote by the agent's reputation.

## How WBFT Consensus Works

```
Agent A (reputation: 0.9) votes ✅ for Fact #42
Agent B (reputation: 0.7) votes ✅ for Fact #42
Agent C (reputation: 0.3) votes ❌ for Fact #42

Weighted score: (0.9 + 0.7) / (0.9 + 0.7 + 0.3) = 0.84
Quorum: ≥ 2 agents must participate
Result: ✅ VERIFIED (confidence: 0.84)
```

## Step 1: Store a Fact

```bash
cortex store --type decision --project swarm-demo "Use PostgreSQL for the user service"
# → Stored fact #42
```

## Step 2: Register Agents

```bash
cortex agent register --name "architect" --weight 0.9
cortex agent register --name "data-engineer" --weight 0.7
cortex agent register --name "junior-dev" --weight 0.3
```

## Step 3: Cast Votes

```bash
# architect agrees
cortex vote 42 --agent architect --approve

# data-engineer agrees
cortex vote 42 --agent data-engineer --approve

# junior-dev disagrees
cortex vote 42 --agent junior-dev --reject
```

## Step 4: Check Consensus

```bash
cortex consensus 42
```

Output:

```
Fact #42: "Use PostgreSQL for the user service"
  Votes: 3 (2 approve, 1 reject)
  Weighted confidence: 0.84
  Status: ✅ VERIFIED
  Quorum: Met (3/2 minimum)
```

## Python API

```python
from cortex import CortexEngine

engine = CortexEngine()

# Store
fact_id = engine.store(
    content="Use PostgreSQL for the user service",
    fact_type="decision",
    project="swarm-demo"
)

# Vote
engine.vote(
    fact_id=fact_id,
    agent_id="architect",
    approve=True,
    weight=0.9
)

engine.vote(
    fact_id=fact_id,
    agent_id="data-engineer",
    approve=True,
    weight=0.7
)

# Check consensus
result = engine.verify_ledger(fact_id)
print(f"Confidence: {result.confidence}")
print(f"Verified: {result.verified}")
```

## Consensus Levels

| Status | Condition | Meaning |
|:---|:---|:---|
| **Verified** | Weighted score ≥ 0.7, quorum met | Agents agree this fact is true |
| **Disputed** | Weighted score 0.4–0.7 | Agents disagree — needs human review |
| **Rejected** | Weighted score < 0.4 | Agents rejected this fact |
| **Pending** | Quorum not met | Not enough agents have voted |

## Why This Matters for Compliance

The EU AI Act (Article 14) requires human oversight for high-risk AI. WBFT consensus provides:

- **Auditable voting records** — who approved what, and when
- **Weighted accountability** — senior agents carry more authority
- **Dispute detection** — automatically flags disagreements
- **Byzantine tolerance** — survives malicious or malfunctioning agents

This makes agent decisions defensible under regulatory scrutiny.

## Next Steps

- [EU AI Act Compliance →](../compliance.md)
- [Architecture →](../architecture.md)
- [CLI Reference →](../cli.md)
