# CORTEX V4.0 — Wave 5: Persistence & Deployment
## Immutable Audit Logs & MCP Server Optimization

**Date:** 2026-02-16  
**Version:** 4.1.0-alpha  
**Status:** Proposal / Design Document  
**Author:** CORTEX Architectural Analysis

---

## Executive Summary

Wave 5 focuses on **production hardening** for CORTEX V4.0's Consensus Layer. Building upon the Reputation-Weighted Consensus (RWC) foundation from Wave 4, this wave delivers:

1. **Immutable Audit Logs** — Cryptographically tamper-evident transaction ledger
2. **MCP Server Optimization** — High-performance Model Context Protocol integration
3. **Deployment Readiness** — Docker, systemd, and cloud-native deployment patterns

### Wave Completion Status

| Wave | Feature | Status |
|------|---------|--------|
| Wave 1 | Core Engine (Facts, Search, Embeddings) | ✅ Complete |
| Wave 2 | Temporal Facts & Transaction Ledger | ✅ Complete |
| Wave 3 | REST API, Auth, Dashboard | ✅ Complete |
| Wave 4 | Consensus Layer (RWC) | ✅ Complete |
| **Wave 5** | **Persistence & Deployment** | 🔄 **Proposed** |
| Wave 6 | Swarm Federation & Bridge Protocols | 📋 Planned |

---

## 1. Immutable Audit Logs

### 1.1 Problem Statement

The current transaction ledger in `engine.py` uses simple SHA-256 chaining:

```python
# Current Implementation (Wave 3)
hash_input = f"{prev_hash}:{project}:{action}:{detail_json}:{ts}"
tx_hash = hashlib.sha256(hash_input.encode()).hexdigest()
```

**Vulnerabilities:**
- ✅ Tamper-evident but not tamper-proof (admins can modify SQLite directly)
- ❌ No external verification mechanism
- ❌ No proof-of-existence timestamping
- ❌ Vulnerable to "God Key" attacks (database admin compromise)

### 1.2 Design Goals

| Goal | Priority | Description |
|------|----------|-------------|
| **Tamper-Proof** | P0 | Cryptographic guarantees against any modification |
| **Verifiable** | P0 | Third parties can verify integrity without trust |
| **Efficient** | P1 | <5ms overhead per transaction |
| **Exportable** | P1 | JSON/CSV export for external auditors |
| **Redundant** | P2 | Multiple storage backends (local + remote hash log) |

### 1.3 Architecture: Hierarchical Ledger System

```
┌─────────────────────────────────────────────────────────────────────┐
│                    IMMUTABLE LEDGER ARCHITECTURE                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│   ┌──────────────┐     ┌──────────────┐     ┌──────────────┐         │
│   │  Fact Store  │     │  Hash Chain  │     │  Merkle Tree │         │
│   │   (SQLite)   │────▶│   (SQLite)   │────▶│  (Periodic)  │         │
│   └──────────────┘     └──────────────┘     └──────────────┘         │
│          │                    │                    │                 │
│          ▼                    ▼                    ▼                 │
│   ┌────────────────────────────────────────────────────────────┐    │
│   │              EXTERNAL SIGNATURE LAYER (Optional)            │    │
│   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │    │
│   │  │  Signify    │  │  OpenPubKey │  │  Anchoring  │         │    │
│   │  │  (Sigstore) │  │  (SSH/PGP)  │  │  (Optional) │         │    │
│   │  └─────────────┘  └─────────────┘  └─────────────┘         │    │
│   └────────────────────────────────────────────────────────────┘    │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

### 1.4 Database Schema Extensions

```sql
-- ============================================================
-- MIGRATION 009: Immutable Ledger Enhancements
-- ============================================================

-- Merkle tree roots for periodic integrity verification
CREATE TABLE merkle_roots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    root_hash       TEXT NOT NULL,              -- SHA-256 of combined TX hashes
    tx_start_id     INTEGER NOT NULL,           -- First TX in this batch
    tx_end_id       INTEGER NOT NULL,           -- Last TX in this batch
    tx_count        INTEGER NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    
    -- Optional: External proof-of-existence
    external_proof  TEXT,                       -- URL or hash of external anchor
    
    -- Signature by "God Key" (if configured)
    signature       TEXT                        -- Ed25519 signature of root_hash
);

CREATE INDEX idx_merkle_range ON merkle_roots(tx_start_id, tx_end_id);

-- Audit log export tracking
CREATE TABLE audit_exports (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    export_type     TEXT NOT NULL,              -- 'json', 'csv', 'chain'
    filename        TEXT NOT NULL,
    file_hash       TEXT NOT NULL,              -- SHA-256 of exported file
    tx_start_id     INTEGER NOT NULL,
    tx_end_id       INTEGER NOT NULL,
    exported_at     TEXT NOT NULL DEFAULT (datetime('now')),
    exported_by     TEXT NOT NULL               -- API key or agent ID
);

-- Tamper detection log (append-only by design)
CREATE TABLE integrity_checks (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    check_type      TEXT NOT NULL,              -- 'merkle', 'chain', 'full'
    status          TEXT NOT NULL,              -- 'ok', 'violation', 'error'
    details         TEXT,                       -- JSON with findings
    started_at      TEXT NOT NULL,
    completed_at    TEXT NOT NULL
);
```

### 1.5 Implementation: Merkle Tree

```python
# cortex/ledger.py
"""
Immutable Ledger — Cryptographic integrity for CORTEX transactions.
"""

import hashlib
import json
from typing import List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class MerkleNode:
    """Node in the Merkle tree."""
    hash: str
    left: Optional['MerkleNode'] = None
    right: Optional['MerkleNode'] = None
    is_leaf: bool = False


class MerkleTree:
    """
    Merkle tree for batch transaction verification.
    Allows efficient verification of large transaction sets.
    """
    
    def __init__(self, leaves: List[str]):
        """
        Build a Merkle tree from leaf hashes.
        
        Args:
            leaves: List of SHA-256 hashes (transaction hashes)
        """
        self.leaves = leaves
        self.root = self._build_tree(leaves)
    
    def _hash_pair(self, left: str, right: str) -> str:
        """Hash two child hashes together."""
        combined = left + right
        return hashlib.sha256(combined.encode()).hexdigest()
    
    def _build_tree(self, hashes: List[str]) -> Optional[MerkleNode]:
        """Recursively build the tree bottom-up."""
        if not hashes:
            return None
        
        if len(hashes) == 1:
            return MerkleNode(hash=hashes[0], is_leaf=True)
        
        # Pair up hashes
        next_level = []
        for i in range(0, len(hashes), 2):
            left = hashes[i]
            right = hashes[i + 1] if i + 1 < len(hashes) else hashes[i]
            combined_hash = self._hash_pair(left, right)
            next_level.append(combined_hash)
        
        return self._build_tree(next_level)
    
    def get_root(self) -> Optional[str]:
        """Get the root hash of the tree."""
        return self.root.hash if self.root else None
    
    def get_proof(self, index: int) -> List[Tuple[str, str]]:
        """
        Get a Merkle proof for a leaf at the given index.
        
        Returns:
            List of (sibling_hash, direction) tuples where direction is 'L' or 'R'
        """
        proof = []
        current_idx = index
        current_level = self.leaves
        
        while len(current_level) > 1:
            next_level = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = current_level[i + 1] if i + 1 < len(current_level) else current_level[i]
                
                if i == current_idx or (i + 1 == current_idx and i + 1 < len(current_level)):
                    # Found our node at this level
                    if current_idx == i:
                        proof.append((right, 'R'))
                    else:
                        proof.append((left, 'L'))
                
                combined = self._hash_pair(left, right)
                next_level.append(combined)
            
            current_idx //= 2
            current_level = next_level
        
        return proof
    
    def verify_proof(self, leaf_hash: str, proof: List[Tuple[str, str]], root: str) -> bool:
        """Verify a Merkle proof."""
        current = leaf_hash
        for sibling, direction in proof:
            if direction == 'L':
                current = self._hash_pair(sibling, current)
            else:
                current = self._hash_pair(current, sibling)
        return current == root


class ImmutableLedger:
    """
    Manages the cryptographic integrity of the CORTEX transaction ledger.
    
    Features:
    - Periodic Merkle tree generation
    - Tamper detection via hash verification
    - Export with integrity proofs
    """
    
    MERKLE_BATCH_SIZE = 1000  # Create Merkle root every N transactions
    
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
    
    def compute_merkle_root(self, start_id: int, end_id: int) -> Optional[str]:
        """Compute Merkle root for a range of transactions."""
        cursor = self.conn.execute(
            "SELECT hash FROM transactions WHERE id >= ? AND id <= ? ORDER BY id",
            (start_id, end_id)
        )
        hashes = [row[0] for row in cursor.fetchall()]
        
        if not hashes:
            return None
        
        tree = MerkleTree(hashes)
        return tree.get_root()
    
    def create_merkle_checkpoint(self) -> Optional[int]:
        """
        Create a Merkle tree checkpoint for recent transactions.
        Returns the checkpoint ID or None if no new transactions.
        """
        # Find last checkpoint
        last = self.conn.execute(
            "SELECT MAX(tx_end_id) FROM merkle_roots"
        ).fetchone()[0] or 0
        
        # Count new transactions
        count = self.conn.execute(
            "SELECT COUNT(*) FROM transactions WHERE id > ?",
            (last,)
        ).fetchone()[0]
        
        if count < self.MERKLE_BATCH_SIZE:
            return None  # Not enough transactions
        
        # Get range
        start = last + 1
        end_row = self.conn.execute(
            "SELECT id FROM transactions WHERE id > ? ORDER BY id LIMIT 1 OFFSET ?",
            (last, self.MERKLE_BATCH_SIZE - 1)
        ).fetchone()
        end = end_row[0] if end_row else start
        
        # Compute root
        root = self.compute_merkle_root(start, end)
        if not root:
            return None
        
        # Store checkpoint
        cursor = self.conn.execute(
            """INSERT INTO merkle_roots 
                (root_hash, tx_start_id, tx_end_id, tx_count) 
                VALUES (?, ?, ?, ?)""",
            (root, start, end, end - start + 1)
        )
        self.conn.commit()
        
        return cursor.lastrowid
    
    def verify_chain_integrity(self) -> dict:
        """
        Verify the integrity of the entire transaction chain.
        
        Returns:
            Dict with verification results
        """
        violations = []
        
        # 1. Verify hash chain continuity
        transactions = self.conn.execute(
            "SELECT id, prev_hash, hash, project, action, detail, timestamp "
            "FROM transactions ORDER BY id"
        ).fetchall()
        
        prev_hash = "GENESIS"
        for tx in transactions:
            tx_id, tx_prev, tx_hash, project, action, detail, ts = tx
            
            # Verify prev_hash matches
            if tx_prev != prev_hash:
                violations.append({
                    "tx_id": tx_id,
                    "type": "chain_break",
                    "expected_prev": prev_hash,
                    "actual_prev": tx_prev
                })
            
            # Verify current hash
            hash_input = f"{tx_prev}:{project}:{action}:{detail}:{ts}"
            computed = hashlib.sha256(hash_input.encode()).hexdigest()
            
            if computed != tx_hash:
                violations.append({
                    "tx_id": tx_id,
                    "type": "hash_mismatch",
                    "computed": computed,
                    "stored": tx_hash
                })
            
            prev_hash = tx_hash
        
        # 2. Verify Merkle roots
        merkles = self.conn.execute(
            "SELECT id, root_hash, tx_start_id, tx_end_id FROM merkle_roots ORDER BY id"
        ).fetchall()
        
        for m in merkles:
            m_id, stored_root, start, end = m
            computed_root = self.compute_merkle_root(start, end)
            
            if computed_root != stored_root:
                violations.append({
                    "merkle_id": m_id,
                    "type": "merkle_mismatch",
                    "range": f"{start}-{end}",
                    "computed": computed_root,
                    "stored": stored_root
                })
        
        return {
            "valid": len(violations) == 0,
            "violations": violations,
            "transactions_checked": len(transactions),
            "merkle_roots_checked": len(merkles)
        }
    
    def export_verifiable_log(self, output_path: str, start_id: int = 1) -> dict:
        """
        Export transactions with integrity proofs.
        
        Args:
            output_path: Where to write the export (JSON format)
            start_id: Starting transaction ID
            
        Returns:
            Export metadata with root hash for verification
        """
        transactions = self.conn.execute(
            "SELECT * FROM transactions WHERE id >= ? ORDER BY id",
            (start_id,)
        ).fetchall()
        
        # Build Merkle tree
        hashes = [tx[4] for tx in transactions]  # hash column
        tree = MerkleTree(hashes)
        root = tree.get_root()
        
        export_data = {
            "export": {
                "version": "1.0",
                "exported_at": datetime.utcnow().isoformat(),
                "start_id": start_id,
                "end_id": transactions[-1][0] if transactions else start_id,
                "transaction_count": len(transactions),
                "merkle_root": root
            },
            "transactions": [
                {
                    "id": tx[0],
                    "project": tx[1],
                    "action": tx[2],
                    "detail": json.loads(tx[3]) if tx[3] else None,
                    "prev_hash": tx[4],
                    "hash": tx[5],
                    "timestamp": tx[6]
                }
                for tx in transactions
            ]
        }
        
        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        # Compute file hash
        with open(output_path, 'rb') as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
        
        # Record export
        self.conn.execute(
            """INSERT INTO audit_exports 
                (export_type, filename, file_hash, tx_start_id, tx_end_id, exported_by)
                VALUES (?, ?, ?, ?, ?, ?)""",
            ("json", output_path, file_hash, 
             export_data["export"]["start_id"],
             export_data["export"]["end_id"],
             "system")
        )
        self.conn.commit()
        
        return {
            "output_path": output_path,
            "file_hash": file_hash,
            "merkle_root": root,
            "transactions": len(transactions)
        }
```

### 1.6 CLI Commands

```bash
# Create a Merkle checkpoint
cortex ledger checkpoint

# Verify ledger integrity
cortex ledger verify
# Output: ✓ Chain valid (10,234 transactions, 10 Merkle roots)
#         ✓ All Merkle roots verified
#         ✓ No tampering detected

# Export verifiable audit log
cortex ledger export --format json --output audit_2024.json

# Import and verify external audit log
cortex ledger verify-external audit_2024.json
```

---

## 2. MCP Server Optimization

### 2.1 Current State Analysis

The existing MCP server (`cortex/mcp_server.py`) provides basic functionality but has limitations:

| Aspect | Current | Target |
|--------|---------|--------|
| Transport | stdio only | stdio + SSE + WebSocket |
| Concurrency | Blocking | Async with connection pooling |
| Caching | None | LRU for embeddings + query results |
| Batching | None | Multi-fact operations |
| Observability | Basic logging | Metrics + structured traces |

### 2.2 Optimized Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    OPTIMIZED MCP SERVER ARCHITECTURE                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│   ┌──────────────────────────────────────────────────────────────┐   │
│   │                      Transport Layer                          │   │
│   │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │   │
│   │  │  stdio   │  │   SSE    │  │  HTTP/2  │  │  WebSocket   │  │   │
│   │  │(default) │  │ (server) │  │(streaming│  │ (real-time)  │  │   │
│   │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────┬───────┘  │   │
│   │       └─────────────┴─────────────┴───────────────┘           │   │
│   │                         │                                     │   │
│   │                         ▼                                     │   │
│   │              ┌─────────────────────┐                         │   │
│   │              │   Protocol Handler  │                         │   │
│   │              │   (MCP 2024-11-05)  │                         │   │
│   │              └──────────┬──────────┘                         │   │
│   └─────────────────────────┼────────────────────────────────────┘   │
│                             │                                        │
│   ┌─────────────────────────┼────────────────────────────────────┐   │
│   │              ┌──────────▼──────────┐                          │   │
│   │              │    Request Router   │                          │   │
│   │              └──────────┬──────────┘                          │   │
│   │                         │                                      │   │
│   │   ┌─────────────────────┼─────────────────────┐               │   │
│   │   │                     │                     │               │   │
│   │   ▼                     ▼                     ▼               │   │
│   │ ┌──────────┐      ┌──────────┐      ┌──────────────────┐     │   │
│   │ │  Tools   │      │Resources │      │  Prompt Templates │     │   │
│   │ │ Registry │      │ Registry │      │    Registry      │     │   │
│   │ └────┬─────┘      └────┬─────┘      └────────┬─────────┘     │   │
│   │      │                 │                     │               │   │
│   └──────┼─────────────────┼─────────────────────┼───────────────┘   │
│          │                 │                     │                   │
│   ┌──────▼─────────────────▼─────────────────────▼───────────────┐   │
│   │                     Engine Layer                               │   │
│   │  ┌──────────────┐  ┌──────────────┐  ┌─────────────────────┐  │   │
│   │  │Query Cache   │  │ Write-Ahead  │  │ Connection Pool     │  │   │
│   │  │   (LRU)      │  │   Buffer     │  │    (SQLite WAL)     │  │   │
│   │  └──────────────┘  └──────────────┘  └─────────────────────┘  │   │
│   └──────────────────────────────────────────────────────────────┘   │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.3 Implementation: Optimized MCP Server

```python
# cortex/mcp_server_v2.py
"""
CORTEX MCP Server v2 — High-Performance Multi-Transport Implementation.

Features:
- Async I/O with connection pooling
- Multiple transports (stdio, SSE, WebSocket)
- Intelligent caching
- Batch operations
- Comprehensive metrics
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, AsyncIterator, Callable, Dict, List, Optional, Union

import sqlite3
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger("cortex.mcp.v2")

# ─────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────

@dataclass
class MCPServerConfig:
    """Configuration for MCP server."""
    db_path: str = "~/.cortex/cortex.db"
    max_workers: int = 4
    query_cache_size: int = 1000
    embedding_cache_size: int = 100
    batch_size: int = 100
    enable_metrics: bool = True
    transport: str = "stdio"  # "stdio", "sse", "websocket"
    
    # SSE/WebSocket specific
    host: str = "127.0.0.1"
    port: int = 9999
    keepalive_interval: float = 30.0


# ─────────────────────────────────────────────────────────────────────────
# Metrics Collection
# ─────────────────────────────────────────────────────────────────────────

@dataclass
class MCPMetrics:
    """Runtime metrics for the MCP server."""
    requests_total: int = 0
    requests_by_tool: Dict[str, int] = field(default_factory=dict)
    request_duration_ms: List[float] = field(default_factory=list)
    cache_hits: int = 0
    cache_misses: int = 0
    errors_total: int = 0
    active_connections: int = 0
    
    def record_request(self, tool: str, duration_ms: float, cached: bool = False):
        self.requests_total += 1
        self.requests_by_tool[tool] = self.requests_by_tool.get(tool, 0) + 1
        self.request_duration_ms.append(duration_ms)
        
        if cached:
            self.cache_hits += 1
        else:
            self.cache_misses += 1
        
        # Keep only last 1000 durations
        if len(self.request_duration_ms) > 1000:
            self.request_duration_ms = self.request_duration_ms[-1000:]
    
    def record_error(self):
        self.errors_total += 1
    
    def get_summary(self) -> dict:
        durations = self.request_duration_ms
        return {
            "requests_total": self.requests_total,
            "requests_by_tool": self.requests_by_tool,
            "avg_duration_ms": sum(durations) / len(durations) if durations else 0,
            "p99_duration_ms": sorted(durations)[int(len(durations) * 0.99)] if len(durations) >= 100 else 0,
            "cache_hit_rate": self.cache_hits / (self.cache_hits + self.cache_misses) if (self.cache_hits + self.cache_misses) > 0 else 0,
            "errors_total": self.errors_total,
            "active_connections": self.active_connections
        }


# ─────────────────────────────────────────────────────────────────────────
# Connection Pool
# ─────────────────────────────────────────────────────────────────────────

class AsyncConnectionPool:
    """
    Async-aware SQLite connection pool.
    
    SQLite connections can't be shared across threads, so we use
    a pool of connections with proper serialization.
    """
    
    def __init__(self, db_path: str, max_connections: int = 5):
        self.db_path = db_path
        self.max_connections = max_connections
        self._pool: asyncio.Queue[sqlite3.Connection] = asyncio.Queue(maxsize=max_connections)
        self._initialized = False
        self._lock = asyncio.Lock()
    
    async def initialize(self):
        """Initialize the connection pool."""
        async with self._lock:
            if self._initialized:
                return
            
            for _ in range(self.max_connections):
                conn = sqlite3.connect(
                    self.db_path,
                    check_same_thread=False,
                    timeout=30.0
                )
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA synchronous=NORMAL")
                await self._pool.put(conn)
            
            self._initialized = True
            logger.info("Connection pool initialized with %d connections", self.max_connections)
    
    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[sqlite3.Connection]:
        """Acquire a connection from the pool."""
        conn = await self._pool.get()
        try:
            yield conn
        finally:
            await self._pool.put(conn)
    
    async def close(self):
        """Close all connections."""
        while not self._pool.empty():
            conn = await self._pool.get()
            conn.close()


# ─────────────────────────────────────────────────────────────────────────
# Optimized MCP Server
# ─────────────────────────────────────────────────────────────────────────

class OptimizedMCPServer:
    """
    High-performance MCP server for CORTEX.
    
    Supports multiple transports and provides:
    - Connection pooling
    - Query caching
    - Batch operations
    - Comprehensive metrics
    """
    
    def __init__(self, config: Optional[MCPServerConfig] = None):
        self.config = config or MCPServerConfig()
        self.metrics = MCPMetrics()
        self.pool: Optional[AsyncConnectionPool] = None
        self.executor = ThreadPoolExecutor(max_workers=self.config.max_workers)
        
        # Cache for search results
        self._query_cache: Dict[str, Any] = {}
        self._cache_lock = asyncio.Lock()
        
        # Running flag
        self._running = False
    
    async def initialize(self):
        """Initialize the server."""
        # Initialize connection pool
        db_path = os.path.expanduser(self.config.db_path)
        self.pool = AsyncConnectionPool(db_path, max_connections=self.config.max_workers)
        await self.pool.initialize()
        
        # Initialize database
        from cortex.migrations import run_migrations
        async with self.pool.acquire() as conn:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(self.executor, run_migrations, conn)
        
        self._running = True
        logger.info("Optimized MCP server initialized")
    
    def _get_cache_key(self, prefix: str, **params) -> str:
        """Generate a cache key from parameters."""
        sorted_params = sorted(params.items())
        param_str = json.dumps(sorted_params, sort_keys=True)
        return f"{prefix}:{hashlib.md5(param_str.encode()).hexdigest()}"
    
    async def _cached_query(self, cache_key: str, query_func: Callable, *args) -> Any:
        """Execute a query with caching."""
        # Check cache
        async with self._cache_lock:
            if cache_key in self._query_cache:
                self.metrics.record_request("cache_hit", 0, cached=True)
                return self._query_cache[cache_key]
        
        # Execute query
        start = time.time()
        result = await query_func(*args)
        duration_ms = (time.time() - start) * 1000
        
        # Cache result
        if len(self._query_cache) < self.config.query_cache_size:
            async with self._cache_lock:
                self._query_cache[cache_key] = result
        
        return result
    
    # ─── MCP Tool Implementations ───────────────────────────────────────
    
    async def cortex_store(
        self,
        project: str,
        content: str,
        fact_type: str = "knowledge",
        tags: str = "[]",
        source: str = "",
        batch: bool = False
    ) -> dict:
        """
        Store a fact (or batch of facts) in CORTEX.
        
        Optimizations:
        - Batch mode for multiple facts
        - Async execution with connection pooling
        """
        from cortex.engine import CortexEngine
        
        start = time.time()
        
        async with self.pool.acquire() as conn:
            # Create engine wrapper
            engine = CortexEngine(self.config.db_path, auto_embed=False)
            engine._conn = conn
            
            try:
                if batch:
                    # Parse batch
                    facts = json.loads(content)  # content is JSON array in batch mode
                    loop = asyncio.get_event_loop()
                    ids = await loop.run_in_executor(
                        self.executor,
                        engine.store_many,
                        facts
                    )
                    result = {
                        "success": True,
                        "fact_ids": ids,
                        "count": len(ids)
                    }
                else:
                    # Single fact
                    parsed_tags = json.loads(tags) if tags else []
                    loop = asyncio.get_event_loop()
                    fact_id = await loop.run_in_executor(
                        self.executor,
                        engine.store,
                        project,
                        content,
                        fact_type,
                        parsed_tags,
                        "stated",
                        source or None,
                        None,
                        None
                    )
                    result = {
                        "success": True,
                        "fact_id": fact_id
                    }
                
                # Invalidate relevant caches
                async with self._cache_lock:
                    keys_to_remove = [
                        k for k in self._query_cache.keys()
                        if k.startswith(f"recall:{project}") or k.startswith(f"search:{project}")
                    ]
                    for k in keys_to_remove:
                        del self._query_cache[k]
                
                duration_ms = (time.time() - start) * 1000
                self.metrics.record_request("cortex_store", duration_ms)
                
                return result
                
            except Exception as e:
                self.metrics.record_error()
                logger.error("Error in cortex_store: %s", e)
                raise
    
    async def cortex_search(
        self,
        query: str,
        project: str = "",
        top_k: int = 5,
        as_of: str = "",
        use_cache: bool = True
    ) -> dict:
        """
        Search CORTEX with caching and performance optimizations.
        """
        from cortex.engine import CortexEngine
        
        cache_key = self._get_cache_key(
            "search",
            query=query,
            project=project,
            top_k=top_k,
            as_of=as_of
        )
        
        async def _do_search():
            async with self.pool.acquire() as conn:
                engine = CortexEngine(self.config.db_path, auto_embed=False)
                engine._conn = conn
                
                loop = asyncio.get_event_loop()
                results = await loop.run_in_executor(
                    self.executor,
                    engine.search,
                    query,
                    project or None,
                    top_k,
                    as_of or None
                )
                
                return [
                    {
                        "fact_id": r.fact_id,
                        "project": r.project,
                        "content": r.content[:200] + "..." if len(r.content) > 200 else r.content,
                        "score": r.score,
                        "consensus_score": getattr(r, 'consensus_score', 1.0)
                    }
                    for r in results
                ]
        
        if use_cache:
            results = await self._cached_query(cache_key, _do_search)
        else:
            results = await _do_search()
        
        duration_ms = 0  # Tracked in _cached_query
        self.metrics.record_request("cortex_search", duration_ms, cached=use_cache)
        
        return {
            "results": results,
            "count": len(results),
            "query": query
        }
    
    async def cortex_recall(
        self,
        project: str,
        limit: int = 20,
        include_deprecated: bool = False,
        use_cache: bool = True
    ) -> dict:
        """
        Recall project facts with caching.
        """
        cache_key = self._get_cache_key(
            "recall",
            project=project,
            limit=limit,
            include_deprecated=include_deprecated
        )
        
        async def _do_recall():
            from cortex.engine import CortexEngine
            
            async with self.pool.acquire() as conn:
                engine = CortexEngine(self.config.db_path, auto_embed=False)
                engine._conn = conn
                
                loop = asyncio.get_event_loop()
                if include_deprecated:
                    facts = await loop.run_in_executor(
                        self.executor, engine.history, project
                    )
                else:
                    facts = await loop.run_in_executor(
                        self.executor, engine.recall, project, limit
                    )
                
                return [
                    {
                        "id": f.id,
                        "content": f.content[:150] + "..." if len(f.content) > 150 else f.content,
                        "type": f.fact_type,
                        "confidence": f.confidence,
                        "consensus_score": f.consensus_score,
                        "tags": f.tags if isinstance(f.tags, list) else []
                    }
                    for f in facts
                ]
        
        if use_cache:
            facts = await self._cached_query(cache_key, _do_recall)
        else:
            facts = await _do_recall()
        
        return {
            "project": project,
            "facts": facts,
            "count": len(facts)
        }
    
    async def cortex_vote(
        self,
        fact_id: int,
        agent: str,
        vote: int,
        reason: str = ""
    ) -> dict:
        """
        Cast a consensus vote on a fact.
        """
        from cortex.engine import CortexEngine
        
        start = time.time()
        
        async with self.pool.acquire() as conn:
            engine = CortexEngine(self.config.db_path, auto_embed=False)
            engine._conn = conn
            
            loop = asyncio.get_event_loop()
            new_score = await loop.run_in_executor(
                self.executor,
                engine.vote,
                fact_id,
                agent,
                vote
            )
            
            duration_ms = (time.time() - start) * 1000
            self.metrics.record_request("cortex_vote", duration_ms)
            
            return {
                "fact_id": fact_id,
                "agent": agent,
                "vote": vote,
                "new_consensus_score": new_score
            }
    
    async def get_metrics(self) -> dict:
        """Return server metrics."""
        return self.metrics.get_summary()
    
    async def health_check(self) -> dict:
        """Health check endpoint."""
        try:
            async with self.pool.acquire() as conn:
                conn.execute("SELECT 1")
            return {"status": "healthy", "database": "connected"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
    
    async def close(self):
        """Shutdown the server."""
        self._running = False
        if self.pool:
            await self.pool.close()
        self.executor.shutdown(wait=True)


# ─────────────────────────────────────────────────────────────────────────
# Transport Implementations
# ─────────────────────────────────────────────────────────────────────────

async def run_stdio_server(config: MCPServerConfig):
    """Run MCP server with stdio transport."""
    server = OptimizedMCPServer(config)
    await server.initialize()
    
    try:
        # Read from stdin, write to stdout
        while server._running:
            line = await asyncio.get_event_loop().run_in_executor(
                None, sys.stdin.readline
            )
            
            if not line:
                break
            
            try:
                request = json.loads(line.strip())
                method = request.get("method")
                params = request.get("params", {})
                request_id = request.get("id")
                
                # Route to appropriate handler
                handler = getattr(server, method, None)
                if handler:
                    result = await handler(**params)
                    response = {
                        "jsonrpc": "2.0",
                        "result": result,
                        "id": request_id
                    }
                else:
                    response = {
                        "jsonrpc": "2.0",
                        "error": {"code": -32601, "message": f"Method not found: {method}"},
                        "id": request_id
                    }
                
                print(json.dumps(response), flush=True)
                
            except json.JSONDecodeError as e:
                print(json.dumps({
                    "jsonrpc": "2.0",
                    "error": {"code": -32700, "message": "Parse error"},
                    "id": None
                }), flush=True)
            except Exception as e:
                print(json.dumps({
                    "jsonrpc": "2.0",
                    "error": {"code": -32603, "message": str(e)},
                    "id": request_id if 'request_id' in locals() else None
                }), flush=True)
                
    finally:
        await server.close()


# Entry point
if __name__ == "__main__":
    import sys
    
    config = MCPServerConfig(
        db_path=os.environ.get("CORTEX_DB", "~/.cortex/cortex.db"),
        transport="stdio"
    )
    
    asyncio.run(run_stdio_server(config))
```

### 2.4 Performance Benchmarks

```python
# tests/benchmark_mcp.py
"""
Benchmark suite for MCP server performance.
"""

import asyncio
import time
import statistics
from cortex.mcp_server_v2 import OptimizedMCPServer, MCPServerConfig


async def benchmark_search():
    """Benchmark search performance with and without cache."""
    config = MCPServerConfig(query_cache_size=1000)
    server = OptimizedMCPServer(config)
    await server.initialize()
    
    queries = [
        "machine learning",
        "neural networks",
        "vector search",
        "consensus algorithm",
        "database optimization"
    ] * 20  # 100 total queries
    
    # Cold cache
    cold_times = []
    for query in queries[:10]:
        start = time.time()
        await server.cortex_search(query, use_cache=True)
        cold_times.append((time.time() - start) * 1000)
    
    # Warm cache (repeated queries)
    warm_times = []
    for query in queries[:10]:  # Same queries
        start = time.time()
        await server.cortex_search(query, use_cache=True)
        warm_times.append((time.time() - start) * 1000)
    
    print(f"Search Performance:")
    print(f"  Cold cache: {statistics.mean(cold_times):.2f}ms avg")
    print(f"  Warm cache: {statistics.mean(warm_times):.2f}ms avg")
    print(f"  Speedup: {statistics.mean(cold_times) / statistics.mean(warm_times):.1f}x")
    
    await server.close()


async def benchmark_batch_store():
    """Benchmark batch store vs individual stores."""
    config = MCPServerConfig()
    server = OptimizedMCPServer(config)
    await server.initialize()
    
    # Individual stores
    facts = [
        {"project": "benchmark", "content": f"Test fact {i}", "fact_type": "knowledge"}
        for i in range(100)
    ]
    
    start = time.time()
    for fact in facts:
        await server.cortex_store(**fact)
    individual_time = (time.time() - start) * 1000
    
    # Batch store
    start = time.time()
    await server.cortex_store(
        project="benchmark",
        content=json.dumps(facts),
        batch=True
    )
    batch_time = (time.time() - start) * 1000
    
    print(f"\nStore Performance (100 facts):")
    print(f"  Individual: {individual_time:.2f}ms ({individual_time/100:.2f}ms/fact)")
    print(f"  Batch: {batch_time:.2f}ms ({batch_time/100:.2f}ms/fact)")
    print(f"  Speedup: {individual_time / batch_time:.1f}x")
    
    await server.close()


# Expected Results:
# Search Performance:
#   Cold cache: 45.23ms avg
#   Warm cache: 0.12ms avg
#   Speedup: 376.9x
#
# Store Performance (100 facts):
#   Individual: 2345.67ms (23.46ms/fact)
#   Batch: 456.78ms (4.57ms/fact)
#   Speedup: 5.1x
```

---

## 3. Deployment Patterns

### 3.1 Docker Deployment

```dockerfile
# Dockerfile.production
FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libsqlite3-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[all]"

# Copy application
COPY cortex/ ./cortex/

# Create non-root user
RUN useradd -m -u 1000 cortex && \
    mkdir -p /data && \
    chown -R cortex:cortex /data

# Environment
ENV CORTEX_DB=/data/cortex.db
ENV CORTEX_ALLOWED_ORIGINS=http://localhost:3000
ENV PYTHONUNBUFFERED=1

USER cortex

# Expose ports
EXPOSE 8484 9999

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8484/health')" || exit 1

# Default: run API server
CMD ["uvicorn", "cortex.api:app", "--host", "0.0.0.0", "--port", "8484"]
```

```yaml
# docker-compose.yml
version: "3.8"

services:
  cortex-api:
    build:
      context: .
      dockerfile: Dockerfile.production
    ports:
      - "8484:8484"
    volumes:
      - cortex-data:/data
    environment:
      - CORTEX_DB=/data/cortex.db
      - CORTEX_RATE_LIMIT=1000
    restart: unless-stopped
    
  cortex-mcp:
    build:
      context: .
      dockerfile: Dockerfile.production
    command: ["python", "-m", "cortex.mcp_server_v2"]
    volumes:
      - cortex-data:/data
    environment:
      - CORTEX_DB=/data/cortex.db
    restart: unless-stopped
    
  # Optional: Prometheus metrics
  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"

volumes:
  cortex-data:
```

### 3.2 systemd Service

```ini
# deploy/cortex.service
[Unit]
Description=CORTEX Sovereign Memory API
After=network.target

[Service]
Type=simple
User=cortex
Group=cortex
WorkingDirectory=/opt/cortex
Environment=CORTEX_DB=/var/lib/cortex/cortex.db
Environment=CORTEX_ALLOWED_ORIGINS=http://localhost:3000
Environment=PYTHONUNBUFFERED=1
ExecStart=/opt/cortex/venv/bin/uvicorn cortex.api:app --host 127.0.0.1 --port 8484
Restart=always
RestartSec=5

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/cortex

[Install]
WantedBy=multi-user.target
```

### 3.3 Kubernetes Deployment

```yaml
# deploy/k8s-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cortex
  labels:
    app: cortex
spec:
  replicas: 3
  selector:
    matchLabels:
      app: cortex
  template:
    metadata:
      labels:
        app: cortex
    spec:
      containers:
      - name: cortex
        image: cortex:v4.1.0
        ports:
        - containerPort: 8484
          name: api
        - containerPort: 9999
          name: mcp
        env:
        - name: CORTEX_DB
          value: "/data/cortex.db"
        volumeMounts:
        - name: data
          mountPath: /data
        livenessProbe:
          httpGet:
            path: /health
            port: 8484
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8484
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: cortex-data
---
apiVersion: v1
kind: Service
metadata:
  name: cortex
spec:
  selector:
    app: cortex
  ports:
  - port: 8484
    targetPort: 8484
    name: api
  - port: 9999
    targetPort: 9999
    name: mcp
  type: ClusterIP
```

---

## 4. Migration Plan

### 4.1 Wave 5 Timeline

```
Week 1-2: Immutable Ledger
├── Migration 009: Merkle tree schema
├── Implementation: MerkleTree class
├── CLI: ledger checkpoint, verify, export
└── Tests: 95% coverage

Week 3-4: MCP Optimization
├── mcp_server_v2.py implementation
├── Connection pooling
├── Caching layer
├── Batch operations
└── Benchmark suite

Week 5: Deployment
├── Dockerfile.production
├── docker-compose.yml
├── systemd service
├── Kubernetes manifests
└── Documentation

Week 6: Integration & Testing
├── End-to-end tests
├── Performance validation
├── Security audit
└── Release candidate
```

### 4.2 Migration Commands

```bash
# Upgrade to Wave 5
cortex migrate

# Create first Merkle checkpoint
cortex ledger checkpoint

# Verify integrity
cortex ledger verify

# Start optimized MCP server
cortex mcp start --transport sse --port 9999

# Run benchmarks
cortex benchmark --suite all
```

---

## 5. Success Criteria

| Metric | Target | Measurement |
|--------|--------|-------------|
| Ledger Verification | <100ms for 10k TX | `cortex ledger verify` |
| MCP Cold Query | <50ms | Benchmark suite |
| MCP Warm Query | <1ms | Benchmark suite |
| MCP Throughput | >1000 req/sec | Load test |
| Cache Hit Rate | >80% | Runtime metrics |
| Docker Image Size | <200MB | `docker images` |
| Memory Usage | <512MB | Container metrics |

---

## Appendix A: API Changes

### New Endpoints

```
POST   /v1/ledger/checkpoint      # Create Merkle checkpoint
GET    /v1/ledger/verify          # Verify integrity
POST   /v1/ledger/export          # Export verifiable log
GET    /v1/mcp/metrics            # MCP server metrics
GET    /v1/mcp/health             # Health check
```

### New CLI Commands

```
cortex ledger checkpoint          # Create checkpoint
cortex ledger verify              # Verify integrity
cortex ledger export              # Export log
cortex mcp start                  # Start MCP server
cortex benchmark                  # Run benchmarks
```

---

**End of Wave 5 Proposal**

*Prepared for CORTEX V4.0 Architecture Review*
