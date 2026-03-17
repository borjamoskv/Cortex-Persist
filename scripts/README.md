# scripts/

> Operational scripts for CORTEX — benchmarks, seeders, gates, daemons, and utilities.

## Categories

| Category | Scripts | Purpose |
|---|---|---|
| **Benchmark** | `benchmark.py`, `benchmark_maas.py`, `benchmark_viz.py` | Performance measurement |
| **Pre-commit** | `entropy_gate.py`, `sovereign_pre_commit.py`, `neural_pre_commit.py`, `sovereign_pre_commit.sh`, `zero_debt.sh` | Code quality gates |
| **Ship Gate** | `ship_gate.py` | Release readiness checks |
| **Daemons** | `academy_trainer_daemon.py`, `void_watcher_daemon.py`, `storm_watcher_l2.py`, `moskv_panopticon.py`, `panopticon_live.py` | Background processes |
| **Seeders** | `seed_*.py`, `backfill_embeddings.py` | Data population |
| **DB Maintenance** | `repair_db.py`, `encrypt_legacy_facts.py`, `repatriate_memories.py` | Database operations |
| **Forge** | `forge_*.py` | Build & generation pipelines |
| **Verify** | `verify_*.py` | Architecture verification |
| **Orchestrators** | `god_mode_orchestrator.py`, `mejoralo_infinito.py`, `orchestrator.py`, `rotate_aether.py` | Meta-execution |
| **MCP / API** | `run_mcp_server.py`, `smoke_test_api.py` | Server launching |
| **NotebookLM** | `fragment_notebooklm.py`, `synthesize_notebooklm.py` | NotebookLM integration |
| **Shell** | `cortex-boot.sh`, `cortex_persist.sh`, `diagnose.sh`, etc. | System operations |

## Safety Guards

Scripts with destructive operations require explicit opt-in:

| Script | Guard |
|---|---|
| `repatriate_memories.py` | `--force` flag or interactive `YES` confirmation |
| `infinite_ouroboros.sh` | `CORTEX_ALLOW_INFINITE=1` env var + `MAX_CYCLES` (default 50) |
| `infinite_investigation.sh` | `CORTEX_ALLOW_INFINITE=1` env var + `MAX_CYCLES` (default 50) |

## `_archive/`

Contains superseded, one-shot, and experimental scripts preserved for archaeological reference. Safe to delete entirely.
