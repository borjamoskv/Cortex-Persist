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
cortex store swarm-demo "Use PostgreSQL for the user service" --type decision
# → Stored fact #42
```

## Step 2: Register Agents

```python
import asyncio
from cortex import CortexEngine


async def main() -> None:
    engine = CortexEngine()

    architect_id = await engine.consensus.register_agent("architect")
    data_engineer_id = await engine.consensus.register_agent("data-engineer")
    junior_dev_id = await engine.consensus.register_agent("junior-dev")

    print(architect_id, data_engineer_id, junior_dev_id)


asyncio.run(main())
```

## Step 3: Cast Votes

```bash
# architect agrees
cortex vote 42 --agent <ARCHITECT_ID> --vote verify

# data-engineer agrees
cortex vote 42 --agent <DATA_ENGINEER_ID> --vote verify

# junior-dev disagrees
cortex vote 42 --agent <JUNIOR_DEV_ID> --vote dispute
```

## Step 4: Read the Result

```python
import asyncio
from cortex import CortexEngine


async def main() -> None:
    engine = CortexEngine()

    fact_id = await engine.store(
        project="swarm-demo",
        content="Use PostgreSQL for the user service",
        fact_type="decision",
    )

    architect_id = await engine.consensus.register_agent("architect")
    data_engineer_id = await engine.consensus.register_agent("data-engineer")

    await engine.vote_v2(fact_id, architect_id, 1, reason="DB choice is validated")
    await engine.vote_v2(fact_id, data_engineer_id, 1, reason="Matches scaling plan")

    fact = await engine.get_fact(fact_id)
    print(f"Consensus score: {fact.consensus_score:.2f}")


asyncio.run(main())
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
