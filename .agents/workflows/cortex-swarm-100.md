---
description: Sovereign Swarm-100 Orchestration and Recruitment
---
// turbo-all
# CORTEX Swarm-100 Operations

This workflow orchestrates massive parallel agent recruitment and mission execution within the CORTEX-Persist ecosystem.

## 1. Specialist Recruitment
Recruit specialized squads for tactical quadrants:
```python
from cortex.engine import CortexEngine
engine = CortexEngine()

# Recruit a P1 Kinetic Squad for capital extraction
await engine.swarm.factory.recruit_squad("P1", size=10)

# Recruit a P0 Integrity Squad for code review
await engine.swarm.factory.recruit_squad("P0", size=5)
```

## 2. Capability Discovery
Recruit agents by specific capability:
```python
# Automatically finds the best skill or forges a JIT specialist
agent_id = await engine.swarm.factory.recruit_by_capability("threejs")
```

## 3. Mission Execution
Dispatch complex tasks across multiple enclaves:
```python
task = "Optimize the data ingestion pipeline and extract capital from available bounties."
results = await engine.swarm.execute_global(task)
```

## 4. Swarm Topologies
- **Frontline**: Bounty hunting and capital extraction.
- **P0**: Integrity, security, and performance audits.
- **P1**: Automation and massive scale operations.
- **P2**: Maintenance and entropy reduction.

## 5. Trust Boundaries (Ω)
All swarm actions are recorded in the `SovereignLedger` with mechanical exergy justifications.
Verify swarm integrity:
```bash
cortex ledger log --project swarm
```
