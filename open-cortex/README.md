# Open CORTEX — Reference Implementation v0.1

> LLM-agnostic memory operating system with metamemory and reconsolidation.

## Quick Start

```bash
# Development (SQLite)
pip install -e ".[dev]"
python -m open_cortex.seed    # Load test data
uvicorn open_cortex.app:app --reload

# Production (Postgres + Docker)
docker-compose up -d
```

## Endpoints

| Method | Path | Description | Conformity |
|:---|:---|:---|:---:|
| POST | `/plan` | LLM generates retrieval plan + JOL | 🥉 |
| POST | `/recall` | Hybrid search (BM25 + ANN) | 🥉 |
| POST | `/write` | Store memory with provenance | 🥉 |
| POST | `/justify` | Response with citations | 🥉 |
| POST | `/reconsolidate` | Versioned truth update | 🥈 |
| GET | `/audit/{memory_id}` | Full change history | 🥈 |
| GET | `/metrics` | Observability (Prometheus) | 🥇 |

## Architecture

```
open_cortex/
├── app.py              # FastAPI application
├── router.py           # All 5+2 endpoints
├── models.py           # Pydantic schemas (Memory, Plan, Justify...)
├── persistence.py      # SQLite/Postgres dual backend
├── search.py           # Hybrid BM25 + ANN retrieval
├── metamemory.py       # FOK/JOL/Brier calibration
├── reconsolidation.py  # Versioning + supersedes logic
├── metrics.py          # Coverage, plan_adherence, etc.
├── seed.py             # Test data loader
└── config.py           # Settings (env vars)
```

## License

Apache 2.0 — See [LICENSE](../LICENSE)
