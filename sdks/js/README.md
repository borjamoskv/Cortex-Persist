# CORTEX JS/TS SDK

Thin, zero-dependency TypeScript client for the [CORTEX Persist API](https://github.com/borjamoskv/Cortex-Persist).

## Install

```bash
# From the cloned repository root
npm install ./sdks/js
```

The package name is reserved as `@cortex-persist/sdk`, but the npm publication
is not live yet. Use the workspace/package directory directly until the first
public release is published.

## Run The Beta API

This SDK talks to the self-hosted beta API. Start that API from the same cloned
repository before running the examples below:

```bash
pip install -e ".[api]"
uvicorn cortex.api:app --port 8000
```

The supported product core remains CLI-first. For the full trust proof,
including fact verification and portable export, use the [canonical demo](../../docs/canonical-demo.md).

## Usage

```typescript
import { Cortex } from '@cortex-persist/sdk'

const ctx = new Cortex({ url: 'http://localhost:8000', apiKey: 'sk-xxx' })

// Store
const factId = await ctx.store('user prefers dark mode', { tags: ['preferences'] })

// Search
const results = await ctx.search('what does the user prefer?', { topK: 3 })
results.forEach(r => console.log(`[${r.score}] ${r.content}`))

// Recall all facts
const facts = await ctx.recall('myproject', 50)

// Verify ledger-wide integrity
const report = await ctx.verify()
console.log(`Ledger valid: ${report.valid} (${report.txChecked} tx checked)`)
```

## API Reference

| Method | Description |
|---|---|
| `store(content, opts?)` | Store a fact → `number` (fact ID) |
| `search(query, opts?)` | Semantic search → `Fact[]` |
| `recall(project, limit?)` | Recall all facts → `Fact[]` |
| `deprecate(factId)` | Soft-delete a fact |
| `verify()` | Ledger-wide integrity check → `LedgerReport` |
| `checkpoint()` | Create Merkle checkpoint |
| `graph(project?, limit?)` | Knowledge graph data |
| `vote(factId, value?)` | Cast consensus vote |

## Outside The Current Supported Core

- public npm publication is not live yet
- the self-hosted API is still beta
- the CLI canonical demo remains the primary path for fact-level verification and export
- `checkpoint()`, `graph()`, and `vote()` should be treated as extended repo surface until the supported-core contract expands

## License

Apache-2.0
