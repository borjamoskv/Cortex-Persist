# CLI Reference

CORTEX provides 15 commands. Run `cortex --help` for the full list.

## Global Options

| Option | Description |
| --- | --- |
| `--version` | Show version and exit |
| `--help` | Show help and exit |

---

## `cortex init`

Initialize the CORTEX database.

```bash
cortex init [--db PATH]
```

| Option | Default | Description |
| --- | --- | --- |
| `--db` | `~/.cortex/cortex.db` | Database path |

---

## `cortex store`

Store a fact in CORTEX.

```bash
cortex store PROJECT CONTENT [OPTIONS]
```

| Argument/Option | Default | Description |
| --- | --- | --- |
| `PROJECT` | *required* | Project name |
| `CONTENT` | *required* | Fact content |
| `--type` | `knowledge` | Fact type (`knowledge`, `decision`, `error`, `config`) |
| `--tags` | — | Comma-separated tags |
| `--confidence` | `stated` | Confidence level |
| `--source` | — | Source of the fact |
| `--db` | `~/.cortex/cortex.db` | Database path |

**Example:**

```bash
cortex store my-api "Rate limit is 100 req/min per API key" --type config --tags "api,limits"
```

---

## `cortex search`

Semantic search across CORTEX memory.

```bash
cortex search QUERY [OPTIONS]
```

| Option | Default | Description |
| --- | --- | --- |
| `--project`, `-p` | — | Scope to project |
| `--top`, `-k` | `5` | Number of results |
| `--db` | `~/.cortex/cortex.db` | Database path |

Uses `all-MiniLM-L6-v2` embeddings via ONNX Runtime for sub-5ms vector search.

---

## `cortex recall`

Load full context for a project.

```bash
cortex recall PROJECT [--db PATH]
```

Returns all active facts grouped by type.

---

## `cortex history`

Temporal query: what did we know at a specific time?

```bash
cortex history PROJECT [--at TIMESTAMP] [--db PATH]
```

| Option | Description |
| --- | --- |
| `--at` | ISO 8601 timestamp for point-in-time query |

---

## `cortex status`

Show CORTEX health and statistics.

```bash
cortex status [--db PATH] [--json-output]
```

| Option | Description |
| --- | --- |
| `--json-output` | Output as JSON instead of table |

---

## `cortex list`

List active facts in a table.

```bash
cortex list [OPTIONS]
```

| Option | Default | Description |
| --- | --- | --- |
| `--project`, `-p` | — | Filter by project |
| `--type` | — | Filter by type |
| `--limit`, `-n` | `20` | Max results |

---

## `cortex edit`

Edit a fact (deprecate old + create new with same metadata).

```bash
cortex edit FACT_ID NEW_CONTENT [--db PATH]
```

---

## `cortex delete`

Soft-delete a fact (deprecate + auto write-back to JSON).

```bash
cortex delete FACT_ID [--reason TEXT] [--db PATH]
```

---

## `cortex sync`

Synchronize `~/.agent/memory/` → CORTEX (incremental).

```bash
cortex sync [--db PATH]
```

Detects changes via SHA-256 hashing and only syncs modified files.

---

## `cortex export`

Export a markdown snapshot for agent consumption.

```bash
cortex export [--db PATH] [--out PATH]
```

| Option | Default | Description |
| --- | --- | --- |
| `--out` | `~/.cortex/context-snapshot.md` | Output path |

---

## `cortex writeback`

Write-back: CORTEX DB → `~/.agent/memory/` JSON files.

```bash
cortex writeback [--db PATH]
```

---

## `cortex migrate`

Import v3.1 data into v4.0.

```bash
cortex migrate [--source PATH] [--db PATH]
```

---

## `cortex time`

Show time tracking summary.

```bash
cortex time [--project PROJECT] [--days N] [--db PATH]
```

---

## `cortex heartbeat`

Record an activity heartbeat.

```bash
cortex heartbeat PROJECT [ENTITY] [OPTIONS]
```

| Option | Description |
| --- | --- |
| `--category`, `-c` | Activity category (auto-classified if omitted) |
| `--branch`, `-b` | Git branch |
