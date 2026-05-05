# CLI Reference

CORTEX exposes many CLI commands because the repository also contains operator and research
tooling. For product integrations, start with the verifiable-memory surface below.

---

## Global Options

| Option | Description |
| :--- | :--- |
| `--version` | Show version and exit |
| `--help` | Show help and exit |
| `--db PATH` | Override database path (default: `~/.cortex/cortex.db`) |

---

## Recommended Core Commands

| Command | Purpose |
| :--- | :--- |
| `cortex init` | Initialize the local ledger |
| `cortex store PROJECT CONTENT` | Persist a fact or decision |
| `cortex search QUERY` | Search persisted memory |
| `cortex recall PROJECT` | Load active project facts |
| `cortex history PROJECT --at ...` | Point-in-time recall |
| `cortex list` | List active facts |
| `cortex edit FACT_ID NEW_CONTENT` | Version a fact |
| `cortex delete FACT_ID` | Soft-delete a fact |
| `cortex status` | Health and DB statistics |
| `cortex verify FACT_ID` | Verify one fact |
| `cortex trust-ledger verify` | Verify the full chain |
| `cortex compliance-report` | Generate a compliance snapshot |

---

## Core Commands In Detail

### `cortex init`

Initialize the CORTEX database.

```bash
cortex init [--db PATH]
```

Safe to call multiple times.

### `cortex store`

Store a fact with automatic ledger entry and embedding.

```bash
cortex store PROJECT CONTENT [OPTIONS]
```

| Option | Default | Description |
| :--- | :--- | :--- |
| `PROJECT` | required | Project namespace |
| `CONTENT` | required | Fact content |
| `--type` | `knowledge` | `knowledge`, `decision`, `ghost`, `preference`, `identity`, `issue`, `error`, `bridge`, `world-model`, `counterfactual` |
| `--tags` | none | Comma-separated tags |
| `--confidence` | `stated` | `C1`, `C2`, `C3`, `C4`, `C5`, `stated`, `inferred` |
| `--source` | auto-detected | Source agent or process |
| `--ai-time` | none | AI generation time used for Chronos metrics |
| `--complexity` | none | `low`, `medium`, `high`, `god`, `impossible` |
| `--parent` | none | Parent decision ID for causal linkage |

Example:

```bash
cortex store my-api "Rate limit is 100 req/min per API key" \
  --type knowledge --tags "api,limits" --confidence C4 --source "agent:claude"
```

### `cortex search`

Semantic search across facts using the configured embedding backend.

```bash
cortex search QUERY [OPTIONS]
```

| Option | Default | Description |
| :--- | :--- | :--- |
| `--project`, `-p` | none | Scope to project |
| `--top`, `-k` | `5` | Number of results |
| `--as-of` | none | Point-in-time query (ISO 8601) |

### `cortex recall`

Load full active context for a project.

```bash
cortex recall PROJECT [--db PATH]
```

### `cortex history`

Query what was known at a specific time.

```bash
cortex history PROJECT [--at TIMESTAMP] [--db PATH]
```

### `cortex status`

Show system health and statistics.

```bash
cortex status [--json-output]
```

### `cortex list`

List active facts in a table.

```bash
cortex list [--project PROJECT] [--type TYPE] [--limit N]
```

### `cortex edit`

Deprecate the old fact and create a new version with updated content.

```bash
cortex edit FACT_ID NEW_CONTENT
```

### `cortex delete`

Soft-delete a fact.

```bash
cortex delete FACT_ID [--reason TEXT]
```

### `cortex verify`

Verify the cryptographic integrity of a specific fact.

```bash
cortex verify FACT_ID
```

### `cortex trust-ledger verify`

Verify the full transaction chain.

```bash
cortex trust-ledger verify
```

When `CORTEX_ENABLE_EXPERIMENTAL_CLI=1`, you can also create checkpoints:

```bash
cortex trust-ledger checkpoint
```

### `cortex compliance-report`

Generate the EU AI Act Article 12 snapshot derived from persisted state.

```bash
cortex compliance-report
```

---

## Additional In-Repo Command Families

When `CORTEX_ENABLE_EXPERIMENTAL_CLI=1`, the root CLI also exposes additional groups such as:

- `memory`, `sync`, `mcp`
- `health`, `security`, `gateway`
- `swarm`, `agent`, `handoff`
- `context`, `compact`, `episodic`
- top-level commands such as `time` and `heartbeat`, plus groups such as `timeline`
These advanced commands and groups are useful for operator workflows, but they are not required to adopt CORTEX Persist
as a verifiable-memory layer. Treat them as advanced surfaces unless your workflow explicitly needs
them.

---

## Boundary Note

If you are onboarding a new project, prefer this sequence:

1. `cortex init`
2. `cortex store`
3. `cortex search` or `cortex recall`
4. `cortex verify`
5. `cortex trust-ledger verify`
6. `cortex compliance-report`
