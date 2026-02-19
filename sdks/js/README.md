# CORTEX JS/TS SDK

Thin, zero-dependency TypeScript client for the [CORTEX Memory API](https://github.com/borjamoskv/cortex).

## Install

```bash
npm install @cortex-memory/sdk
```

## Usage

```typescript
import { Cortex } from '@cortex-memory/sdk'

const ctx = new Cortex({ url: 'http://localhost:8000', apiKey: 'sk-xxx' })

// Store
const factId = await ctx.store('user prefers dark mode', { tags: ['preferences'] })

// Search (semantic + Graph RAG)
const results = await ctx.search('what does the user prefer?', { topK: 3 })
results.forEach(r => console.log(`[${r.score}] ${r.content}`))

// Recall all facts
const facts = await ctx.recall('myproject', 50)

// Verify ledger integrity
const report = await ctx.verify()
console.log(`Ledger valid: ${report.valid} (${report.txChecked} tx checked)`)

// Knowledge graph
const graph = await ctx.graph('myproject')

// Time-travel query
const past = await ctx.search('status', { asOf: '2026-01-15T00:00:00' })
```

## API Reference

| Method | Description |
|---|---|
| `store(content, opts?)` | Store a fact → `number` (fact ID) |
| `search(query, opts?)` | Semantic search → `Fact[]` |
| `recall(project, limit?)` | Recall all facts → `Fact[]` |
| `deprecate(factId)` | Soft-delete a fact |
| `verify()` | Ledger integrity check → `LedgerReport` |
| `checkpoint()` | Create Merkle checkpoint |
| `graph(project?, limit?)` | Knowledge graph data |
| `vote(factId, value?)` | Cast consensus vote |

## License

Apache-2.0
