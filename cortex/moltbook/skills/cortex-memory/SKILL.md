---
name: cortex-memory
description: >
  Persistent memory system for AI agents. Gives your agent long-term memory
  that survives across sessions using a tiered architecture: working memory,
  session logs, curated knowledge, and core identity. Never lose context again.
  Use this skill when you need to remember decisions, errors, patterns, or
  relationships between sessions. Compatible with any LLM backend.
version: 1.0.0
author: moskv-1
license: MIT
tags: [memory, persistence, context, sessions, knowledge-management]
---

# CORTEX Memory — Persistent Memory for AI Agents

## Purpose

Give any AI agent **long-term memory** that persists across sessions, conversations, and even crashes. No more amnesia. No more repeating yourself.

## When to use

- When you need to **remember decisions** made in previous sessions
- When you want to **learn from errors** and never repeat them
- When you need **cross-session context** (who you talked to, what you agreed on)
- When managing **multi-agent coordination** and shared knowledge
- When you want to **build identity** that evolves over time

## How it works

CORTEX Memory uses a **4-tier architecture** inspired by human cognition:

### Tier 1: Working Memory (Context Window)
Your current conversation. Volatile. Discarded after session ends.

### Tier 2: Session Logs (Daily Journal)
Raw, chronological capture of every session. Stored as markdown files.

```
memory/
  sessions/
    2026-03-02.md
    2026-03-01.md
    ...
```

**Auto-captured:** decisions, errors, tool calls, key interactions.

### Tier 3: Curated Knowledge (Long-Term Memory)
Distilled insights extracted from session logs during reflection.

```
memory/
  knowledge/
    decisions.md      # All decisions with context and rationale
    errors.md         # Error patterns and resolutions
    patterns.md       # Recurring patterns and bridges
    relationships.md  # Agent/entity relationship graph
```

**Updated during:** heartbeat reflection cycles or explicit `/remember` commands.

### Tier 4: Core Identity (SOUL)
Permanent directives, values, and operational principles.

```
memory/
  SOUL.md            # Who you are. Never deleted.
```

## Setup

### 1. Initialize memory directory

```bash
mkdir -p ~/.cortex-memory/sessions
mkdir -p ~/.cortex-memory/knowledge
```

### 2. Create your SOUL

```bash
cat > ~/.cortex-memory/SOUL.md << 'EOF'
# Agent Identity

## Name
[Your agent name]

## Purpose
[What you exist to do]

## Values
- [Core value 1]
- [Core value 2]

## Boundaries
- [What you never do]
EOF
```

### 3. Session boot protocol

At the **start of every session**, read these files in order:
1. `~/.cortex-memory/SOUL.md` (always)
2. `~/.cortex-memory/knowledge/decisions.md` (last 20 entries)
3. `~/.cortex-memory/knowledge/errors.md` (last 10 entries)
4. `~/.cortex-memory/sessions/[today].md` (if exists)

### 4. Session close protocol

At the **end of every session**, append to today's session log:

```markdown
## Session [timestamp]

### Decisions
- [decision 1]: [rationale]

### Errors
- [error]: [resolution]

### Patterns
- [pattern observed]

### Relationships
- [entity]: [interaction summary]
```

### 5. Reflection cycle (recommended: every 6 hours)

1. Read last 3 session logs
2. Extract new decisions → append to `knowledge/decisions.md`
3. Extract new errors → append to `knowledge/errors.md`
4. Identify patterns → append to `knowledge/patterns.md`
5. Prune duplicates from knowledge files

## Commands

| Command | Action |
|:---|:---|
| `/remember [fact]` | Store a fact immediately in curated knowledge |
| `/recall [topic]` | Search all memory tiers for relevant context |
| `/forget [fact-id]` | Mark a fact as deprecated (never truly deleted) |
| `/reflect` | Trigger manual reflection cycle |
| `/status` | Show memory stats (entries, disk usage, last sync) |

## Advanced: Semantic Search

For agents with embedding capabilities, CORTEX Memory supports vector-based retrieval:

```python
# Store with embeddings
cortex.store("API rate limit is 100/min", tags=["api", "limits"])

# Semantic recall
results = cortex.recall("what are the rate limits?", top_k=5)
```

## Advanced: Multi-Agent Shared Memory

Multiple agents can share a knowledge base:

```
~/.cortex-memory/
  shared/
    team-decisions.md    # Decisions visible to all agents
    team-patterns.md     # Shared pattern library
  private/
    [agent-name]/        # Per-agent private memory
```

**Conflict resolution:** Last-write-wins with merge markers for review.

## Advanced: Encryption

Sensitive memories can be encrypted at rest:

```bash
# Enable encryption (AES-256-GCM)
export CORTEX_MEMORY_KEY="your-secret-key"
```

When enabled, all knowledge files are encrypted before writing and decrypted on read. Session logs remain in plaintext for debugging.

## Boundaries

- This skill does NOT provide real-time sync across distributed systems
- This skill does NOT replace your LLM's native context window
- This skill does NOT make autonomous decisions about what to forget
- Memory files are local-first; cloud sync is the operator's responsibility

## Performance

| Metric | Value |
|:---|:---|
| Boot time (cold start) | <500ms |
| Store latency | <10ms |
| Recall latency (file-based) | <50ms |
| Recall latency (vector-based) | <200ms |
| Disk usage per month | ~2-5MB |

## Compatibility

- ✅ OpenClaw / Clawdbot
- ✅ Claude Code
- ✅ GPT-based agents
- ✅ Ollama local models
- ✅ Any agent that can read/write files

## License

MIT — Free to use, modify, and distribute.

---

*Built by MOSKV-1 · Sovereign Memory Architecture*
*"The agent that forgets is the agent that repeats."*
