# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [4.0.0] - 2026-02-18

### Added
- **Sovereign Engine**: New `CortexEngine` with modular mixin architecture (Store, Query, Consensus).
- **Consensus Layer**: Reputation-Weighted Consensus (RWC) for multi-agent fact verification.
- **Immutable Ledger**: Hash-chained transaction log with Merkle tree checkpoints for tamper-evident history.
- **Temporal Facts**: Native support for `valid_from` and `valid_until` in knowledge facts.
- **MCP Server**: Full implementation of Model Context Protocol for AI agent integration.
- **Async API**: High-performance FastAPI backend with connection pooling and async SQLite.
- **Industrial Noir UI**: New dashboard aesthetic with "Cyber Lime" and "Abyssal Black" theme.
- **Internationalization**: Localized error messages and responses (en, es).

### Changed
- **License**: Changed from MIT to Business Source License (BSL) 1.1.
- **Database**: Migrated to `aiosqlite` for all core engine operations.
- **Search**: Replaced legacy search with `sqlite-vec` + ONNX quantized embeddings (384-dim).

### Fixed
- Auth: Fixed 422 error on missing Authorization header (now correctly returns 401).
- API: Added missing `source` and `meta` fields to `StoreRequest` model.
- Security: Rotated compromised credentials and enforced strict CORS policies.
