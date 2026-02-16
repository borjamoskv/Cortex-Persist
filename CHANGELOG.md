# Changelog

All notable changes to CORTEX will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] — 2026-02-16

### Added

- **Core Engine** — Fact storage with hash-chained transaction ledger
- **Semantic Search** — Local ONNX embeddings + sqlite-vec vector search
- **REST API** — FastAPI with SHA-256 hashed API key authentication
- **CLI** — 15 commands: init, store, search, recall, history, status, sync, export, edit, delete, list, time, migrate, writeback, heartbeat
- **Daemon** — Site monitoring, ghost detection, memory freshness alerts, SSL cert checks
- **Dashboard** — Embedded Industrial Noir UI with Chart.js visualizations
- **Time Tracking** — Heartbeat-based automatic activity classification
- **Sync Engine** — Bidirectional JSON ↔ DB with SHA-256 change detection
- **Temporal Queries** — Point-in-time fact recall with `valid_from` / `valid_until`
- **Client Library** — `CortexClient` for programmatic API access
- PEP 561 `py.typed` marker for type hint consumers

## [0.1.1] — 2026-02-16

### Fixed

- **Critical Engine Syntax Error**: Resolved duplicated function definition in `CortexEngine` blocking import.
- **API Security**: Implemented strict authentication for GET `/v1/search` and dashboard endpoints to prevent unauthorized access.
- **Input Validation**: Added input length enforcement for fact content and project names.

### Changed

- **MEJORAlo Kimi Workflow**: Elevated `kimi.md` to LEGENDARY status with premium alerts and optimized instructions.
