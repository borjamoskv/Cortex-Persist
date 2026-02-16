# CORTEX

**Local-first sovereign memory infrastructure for AI agents.**

Semantic search, temporal queries, and hash-chained transaction ledger — all running locally on SQLite. Zero network dependencies.

---

## Why CORTEX?

- 🧠 **Sovereign** — Your data stays on your machine. No cloud, no API keys, no vendor lock-in.
- ⚡ **Sub-5ms embeddings** — ONNX Runtime runs `all-MiniLM-L6-v2` locally.
- ⏰ **Temporal** — Ask "what did we know last Tuesday?" with point-in-time queries.
- 🔐 **Tamper-proof** — Every mutation is recorded in a hash-chained transaction ledger.
- 📊 **Observable** — Built-in dashboard, time tracking, and daemon monitoring.

## Quick Install

```bash
pip install cortex-memory
```

```bash
cortex init
cortex store my-project "FastAPI uses Pydantic for validation" --tags "fastapi,python"
cortex search "how does validation work?"
```

[Get started →](quickstart.md){ .md-button .md-button--primary }
[View on GitHub →](https://github.com/borjamoskv/cortex){ .md-button }
