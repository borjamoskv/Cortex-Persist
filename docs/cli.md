# CLI Reference

CORTEX provides **38 commands** organized by function. Run `cortex --help` for the full list.

---

## Global Options

| Option | Description |
|:---|:---|
| `--version` | Show version and exit |
| `--help` | Show help and exit |
| `--db PATH` | Override database path (default: `~/.cortex/cortex.db`) |

---

## Core Commands

### `cortex init`

Initialize the CORTEX database with the full schema.

```bash
cortex init [--db PATH]
```

Safe to call multiple times — idempotent.

---

### `cortex store`

Store a fact with automatic hash-chain ledger entry and embedding.

```bash
cortex store PROJECT CONTENT [OPTIONS]
```

| Option | Default | Description |
|:---|:---|:---|
| `PROJECT` | *required* | Project namespace |
| `CONTENT` | *required* | Fact content |
| `--type` | `knowledge` | `knowledge`, `decision`, `error`, `ghost`, `config`, `bridge`, `axiom`, `rule` |
| `--tags` | — | Comma-separated tags |
| `--confidence` | `stated` | `stated`, `inferred`, `observed`, `verified`, `disputed` |
| `--source` | auto-detected | Source agent or process |
| `--ai-time` | — | Estimated AI time saved (Chronos integration) |
| `--complexity` | — | Task complexity rating (1-10) |

**Example:**

```bash
cortex store my-api "Rate limit is 100 req/min per API key" \
  --type config --tags "api,limits" --source "agent:claude"
```

---

### `cortex search`

Semantic search across all facts using vector embeddings.

```bash
cortex search QUERY [OPTIONS]
```

| Option | Default | Description |
|:---|:---|:---|
| `--project`, `-p` | — | Scope to project |
| `--top`, `-k` | `5` | Number of results |
| `--as-of` | — | Point-in-time query (ISO 8601) |

Uses `all-MiniLM-L6-v2` embeddings via ONNX Runtime for sub-5ms vector search.

---

### `cortex recall`

Load full context for a project.

```bash
cortex recall PROJECT [--db PATH]
```

Returns all active facts grouped by type (knowledge, decisions, errors, etc.).

---

### `cortex history`

Temporal query: what did we know at a specific time?

```bash
cortex history PROJECT [--at TIMESTAMP] [--db PATH]
```

---

### `cortex status`

Show CORTEX health and statistics.

```bash
cortex status [--json-output]
```

Displays: total facts, active facts, embeddings, transactions, DB size, projects.

---

### `cortex list`

List active facts in a table.

```bash
cortex list [--project PROJECT] [--type TYPE] [--limit N]
```

---

### `cortex edit`

Edit a fact (deprecates old, creates new with same metadata).

```bash
cortex edit FACT_ID NEW_CONTENT
```

---

### `cortex delete`

Soft-delete a fact (mark as deprecated).

```bash
cortex delete FACT_ID [--reason TEXT]
```

---

## Trust & Verification Commands

### `cortex verify`

Cryptographic verification certificate for a single fact.

```bash
cortex verify FACT_ID
```

Output includes: hash chain status, Merkle root, consensus score, timestamp.

---

### `cortex ledger`

Ledger operations.

```bash
cortex ledger verify    # Full hash chain integrity check
cortex ledger stats     # Ledger statistics
```

---

### `cortex compliance-report`

Generate EU AI Act Article 12 compliance snapshot.

```bash
cortex compliance-report [--format json|text]
```

Outputs: compliance score (0-5), requirement mapping, evidence references.

---

### `cortex audit-trail`

Generate a timestamped, hash-verified audit log.

```bash
cortex audit-trail [--project PROJECT] [--limit N]
```

---

### `cortex vote`

Cast a consensus vote on a fact.

```bash
cortex vote FACT_ID --agent AGENT_ID --vote [verify|dispute]
```

---

## Sync & Export Commands

### `cortex sync`

Synchronize `~/.agent/memory/` JSON files → CORTEX DB (incremental, SHA-256 change detection).

```bash
cortex sync
```

---

### `cortex export`

Export a markdown snapshot for agent consumption.

```bash
cortex export [--out PATH]
```

Default output: `~/.cortex/context-snapshot.md`

---

### `cortex writeback`

Write-back: CORTEX DB → `~/.agent/memory/` JSON files.

```bash
cortex writeback
```

---

### `cortex migrate`

Import data from older versions.

```bash
cortex migrate [--source PATH]
```

---

## Time Tracking Commands

### `cortex time`

Show time tracking summary (WakaTime-like).

```bash
cortex time [--project PROJECT] [--days N]
```

---

### `cortex heartbeat`

Record an activity heartbeat for automatic time tracking.

```bash
cortex heartbeat PROJECT [ENTITY] [--category CATEGORY] [--branch BRANCH]
```

---

### `cortex timeline`

Visual temporal memory browsing.

```bash
cortex timeline PROJECT [--days N]
```

---

## Memory Intelligence Commands

### `cortex compact`

Run auto-compaction strategies on project memory.

```bash
cortex compact [--project PROJECT] [--strategy dedup|merge|prune|all]
```

---

### `cortex episodic`

Episodic memory operations.

```bash
cortex episodic observe    # Capture session snapshot
cortex episodic recall     # Restore from episode
cortex episodic replay     # Replay decision chain
```

---

### `cortex context`

Context window management for agents.

```bash
cortex context rebuild PROJECT    # Rebuild context from memory
cortex context export PROJECT     # Export for agent consumption
```

---

## Agent & Swarm Commands

### `cortex handoff`

Structured agent-to-agent context transfer.

```bash
cortex handoff generate    # Generate handoff document
cortex handoff receive     # Receive and import handoff
```

---

### `cortex ghost`

Ghost (incomplete work) management.

```bash
cortex ghost list          # List all ghosts
cortex ghost resolve ID    # Mark resolved
```

---

### `cortex swarm`

Multi-agent swarm coordination.

```bash
cortex swarm dispatch      # Dispatch a consensus mission
cortex swarm status        # Check mission status
```

---

## Infrastructure Commands

### `cortex daemon`

Background daemon management.

```bash
cortex daemon start        # Start the watchdog daemon
cortex daemon stop         # Stop the daemon
cortex daemon install      # Install as system service
cortex daemon status       # Check daemon health
```

The daemon runs 13 specialized monitors: site health, SSL certs, disk space, ghost detection, security scanning, and more.

---

### `cortex autorouter`

AI model auto-selection daemon.

```bash
cortex autorouter start    # Start model routing
cortex autorouter stop     # Stop
cortex autorouter status   # Current model state
cortex autorouter history  # View switch history
```

---

### `cortex mejoralo`

Code quality engine (X-Ray 13D scanner).

```bash
cortex mejoralo scan PATH  # Analyze code quality
cortex mejoralo fix PATH   # Auto-fix issues
```

---

### `cortex entropy`

Entropy monitoring for codebase health.

```bash
cortex entropy scan        # Measure codebase entropy
cortex entropy dashboard   # Visual entropy report
```

---

### `cortex purge`

Data cleanup operations.

```bash
cortex purge --project PROJECT [--before DATE] [--dry-run]
```

---

### `cortex tips`

Developer tips and best practices engine.

```bash
cortex tips [--category CATEGORY]
```

---

### `cortex reflect`

Meta-cognitive session analysis.

```bash
cortex reflect              # Analyze current session patterns
```

---

## Makefile Shortcuts

```bash
make test          # Run all tests (60s timeout)
make test-fast     # Exclude slow tests (no torch imports)
make test-slow     # Only slow tests (graph RAG, embeddings)
make lint          # Run ruff linter
make format        # Auto-format with ruff
make docs          # Build mkdocs site
make serve-docs    # Live preview docs
```
