---
name: swarm-coordinator
description: >
  Multi-agent coordination skill for AI agent swarms. Enables task decomposition, 
  delegation, consensus, and result aggregation across multiple agents. Use when
  a task is too complex for a single agent, when you need parallel execution,
  or when multiple specialized agents need to collaborate on a shared goal.
version: 1.0.0
author: moskv-1
license: MIT
tags: [swarm, multi-agent, coordination, delegation, consensus, parallel]
---

# Swarm Coordinator — Multi-Agent Orchestration

## Purpose

Coordinate **multiple AI agents** to solve complex problems collaboratively. Decompose tasks, delegate to specialists, aggregate results, and resolve conflicts — all autonomously.

## When to use

- When a task requires **multiple specializations** (e.g., research + coding + review)
- When you need **parallel execution** to save time
- When **consensus** is needed across multiple agents
- When building **agent pipelines** (output of one feeds into another)
- When a single agent's context window is insufficient

## How it works

### Task Lifecycle

```
[INTENT] → [DECOMPOSE] → [DELEGATE] → [EXECUTE] → [AGGREGATE] → [DELIVER]
```

### 1. Task Decomposition

Break complex tasks into atomic subtasks:

```markdown
## Mission: Build a landing page

### Subtasks:
1. [RESEARCH] Analyze competitor landing pages (Agent: Researcher)
2. [DESIGN] Create wireframe based on research (Agent: Designer)  
3. [CODE] Implement design in HTML/CSS (Agent: Developer)
4. [REVIEW] Quality check final output (Agent: Reviewer)
```

### 2. Agent Roles

Define specialized agents with clear capabilities:

```yaml
agents:
  researcher:
    capabilities: [web-search, summarization, data-extraction]
    cost_per_task: low
    reliability: 0.95
    
  developer:
    capabilities: [coding, debugging, deployment]
    cost_per_task: medium
    reliability: 0.90
    
  reviewer:
    capabilities: [code-review, testing, quality-scoring]
    cost_per_task: low
    reliability: 0.98
```

### 3. Delegation Protocol

```
COORDINATOR → AGENT: {
  task_id: "uuid",
  description: "what to do",
  context: "relevant background",
  constraints: ["max 500 tokens", "respond in JSON"],
  deadline: "2min",
  fallback: "agent_b"
}

AGENT → COORDINATOR: {
  task_id: "uuid",
  status: "complete|failed|partial",
  result: "output data",
  confidence: 0.85,
  cost: { tokens: 1500, time_ms: 3200 }
}
```

### 4. Consensus Mechanisms

When multiple agents provide conflicting results:

| Method | When to use | How it works |
|:---|:---|:---|
| **Majority Vote** | Simple decisions | 3+ agents vote, majority wins |
| **Weighted Average** | Numerical outputs | Weight by agent reliability score |
| **Expert Override** | Domain-specific | Highest expertise agent decides |
| **Byzantine Consensus** | Adversarial environments | 2/3 agreement required |

### 5. Result Aggregation

```markdown
## Mission Report

### Results
- Research: ✅ Complete (confidence: 0.92)
- Design: ✅ Complete (confidence: 0.87)
- Code: ✅ Complete (confidence: 0.90)
- Review: ⚠️ Issues found (2 critical, 5 minor)

### Aggregated Output
[Final deliverable with all subtask outputs merged]

### Cost Summary
- Total tokens: 12,500
- Total time: 45s
- Total cost: $0.04
```

## Commands

| Command | Action |
|:---|:---|
| `/swarm mission [description]` | Start a new coordinated mission |
| `/swarm status` | Check progress of active missions |
| `/swarm agents` | List available agents and their status |
| `/swarm cancel [mission_id]` | Cancel an active mission |
| `/swarm history` | View past mission results |

## Advanced: Pipeline Mode

Chain agents sequentially:

```
Research → Summarize → Code → Test → Deploy
   ↓          ↓         ↓      ↓       ↓
 Agent A   Agent B   Agent C  Agent D  Agent E
```

Each agent's output becomes the next agent's input. If any step fails, the pipeline halts and reports the failure point.

## Advanced: Self-Healing

If an agent fails or times out:
1. Retry with same agent (1x)
2. Delegate to fallback agent
3. Decompose further (split subtask into smaller pieces)
4. Escalate to coordinator for manual resolution

## Boundaries

- Does NOT manage agent lifecycle (creation/destruction)
- Does NOT handle inter-agent authentication
- Does NOT provide real-time streaming between agents
- Requires agents to be reachable via function calls or HTTP

## Performance

| Metric | Value |
|:---|:---|
| Max concurrent agents | 10 |
| Task decomposition time | <1s |
| Delegation overhead | <100ms per agent |
| Consensus resolution | <500ms |

---

*Built by MOSKV-1 · LEGION Protocol*
*"One agent is smart. A swarm is sovereign."*
