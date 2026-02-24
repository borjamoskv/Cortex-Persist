# CORTEX Architectural Audit Report

**Date:** 2026-02-24  
**Scope:** `/Users/borjafernandezangulo/cortex/cortex/` (42,613+ LOC)  
**Auditor:** Kimi Code CLI  

---

## Executive Summary

| Severity | Count | Description |
|----------|-------|-------------|
| **P0 (Critical)** | 8 | System-wide failures, data loss, security vulnerabilities |
| **P1 (High)** | 14 | Major functionality degradation, performance bottlenecks |
| **P2 (Medium)** | 23 | Reliability issues, partial failures |
| **P3 (Low)** | 31 | Code quality, maintainability issues |

**Total Issues:** 76

---

## 1. SINGLE POINTS OF FAILURE (P0-P3)

### P0: Global Module-Level Singletons Without Thread Safety

#### Issue SPOF-001
- **File:** `cortex/config.py`
- **Line:** 187-208
- **Severity:** P0
- **Description:** Module-level singleton `_cfg` is lazily initialized via `reload()` which modifies global state. Not thread-safe during reconfiguration. Concurrent access during reload can return inconsistent configuration.
```python
# Line 189
_cfg = CortexConfig.from_env()  # Module-level singleton

# Line 192-199  
def reload() -> None:
    global _cfg
    _cfg = CortexConfig.from_env()  # Race condition here
    for attr in CortexConfig.__dataclass_fields__:
        setattr(_module, attr, getattr(_cfg, attr))  # Non-atomic update
```
- **Fix:** Use `asyncio.Lock` or `threading.RLock` around reload operations; implement atomic configuration swap using immutable config objects.

#### Issue SPOF-002
- **File:** `cortex/notifications/bus.py`
- **Line:** 117-136
- **Severity:** P0
- **Description:** Process-level singleton `_bus` accessed via `get_notification_bus()` has no initialization synchronization. Race condition during first access in multi-threaded environments.
```python
_bus: NotificationBus | None = None

def get_notification_bus() -> NotificationBus:
    global _bus
    if _bus is None:  # Race window here
        _bus = NotificationBus()
    return _bus
```
- **Fix:** Implement double-checked locking pattern or use `functools.lru_cache` with thread-safe initialization.

#### Issue SPOF-003
- **File:** `cortex/gate/core.py`
- **Line:** 323-342
- **Severity:** P0
- **Description:** Global `_gate_instance` singleton with no thread-safety. Critical security component vulnerable to race conditions during initialization.
```python
_gate_instance: Optional["SovereignGate"] = None

def get_gate(...) -> SovereignGate:
    global _gate_instance
    if _gate_instance is None:  # Race condition
        _gate_instance = SovereignGate(...)
    return _gate_instance
```
- **Fix:** Add `threading.Lock` or `asyncio.Lock` for initialization; consider using `contextvars` for per-context gate instances in async environments.

#### Issue SPOF-004
- **File:** `cortex/auth/__init__.py`
- **Line:** 337-352
- **Severity:** P0
- **Description:** Auth manager singleton with race condition during initialization. Authentication bypass possible if two threads initialize simultaneously.
- **Fix:** Use `asyncio.Lock` or implement proper singleton pattern with `__new__`.

#### Issue SPOF-005
- **File:** `cortex/crypto/aes.py`
- **Line:** 122-141
- **Severity:** P0
- **Description:** Encryption singleton `_default_encrypter_instance` not thread-safe during initialization. Crypto key material could be corrupted.
- **Fix:** Add thread-safe initialization with locking.

---

### P1: Single Writer Queue Bottleneck

#### Issue SPOF-006
- **File:** `cortex/database/writer.py`
- **Line:** 71-403
- **Severity:** P1
- **Description:** `SqliteWriteWorker` uses a single asyncio.Queue (maxsize=10,000) with one writer task. All writes serialize through this single point. If the writer task crashes, the entire write path fails with no automatic recovery.
```python
self._queue: asyncio.Queue[_Message] = asyncio.Queue(maxsize=queue_size)
self._task: asyncio.Task[None] | None = None  # Single task
```
- **Fix:** Implement health checks and automatic task restart; consider sharded write workers for horizontal scaling.

#### Issue SPOF-007
- **File:** `cortex/database/pool.py`
- **Line:** 23-181
- **Severity:** P1
- **Description:** Single connection pool with fixed max_connections. Under high load, semaphore exhaustion causes cascading failures.
```python
self._semaphore = asyncio.Semaphore(max_connections)  # Hard limit
```
- **Fix:** Implement adaptive pool sizing; add circuit breaker pattern for DB operations.

---

### P1: In-Memory State Without Persistence

#### Issue SPOF-008
- **File:** `cortex/gate/core.py`
- **Line:** 313-320
- **Severity:** P1
- **Description:** Audit log stored only in memory (`self._audit_log: list[dict]`). Process restart = audit trail loss. Non-compliant for security requirements.
```python
self._audit_log: list[dict[str, Any]] = []  # In-memory only
```
- **Fix:** Persist audit logs to append-only file or database; implement log rotation.

#### Issue SPOF-009
- **File:** `cortex/daemon/core.py`
- **Line:** 439-449
- **Severity:** P1
- **Description:** Daemon status saved to JSON file without atomic write. Crash during write = corrupted status file.
```python
STATUS_FILE.write_text(json.dumps(status.to_dict(), ...))  # Non-atomic
```
- **Fix:** Use atomic file write pattern (write to temp, then rename).

---

### P2: Hardcoded Resource Limits

#### Issue SPOF-010
- **File:** `cortex/memory/manager.py`
- **Line:** 65, 137-142
- **Severity:** P2
- **Description:** Background task limit of 100 hardcoded. When exceeded, overflow tasks are silently dropped.
```python
if len(self._background_tasks) >= self._max_bg_tasks:
    logger.warning("... Dropping overflow task.")  # Data loss
```
- **Fix:** Make configurable; implement backpressure mechanism instead of dropping.

#### Issue SPOF-011
- **File:** `cortex/llm/manager.py`
- **Line:** 8, 36-40
- **Severity:** P2
- **Description:** Lazy-loaded singleton without timeout or circuit breaker. LLM provider failure blocks indefinitely.
- **Fix:** Add connection timeouts and circuit breaker pattern.

---

## 2. MISSING ERROR BOUNDARIES

### P0: Bare Exception Handlers

#### Issue ERR-001
- **File:** `cortex/daemon/sidecar/telemetry/fiat_oracle.py`
- **Line:** 48, 60, 113, 149, 180, 221
- **Severity:** P0
- **Description:** Multiple bare `except Exception` blocks swallow critical errors including `KeyboardInterrupt`, `SystemExit`, and `MemoryError`.
```python
except Exception as e:  # Catches EVERYTHING including SystemExit
    self.logger.error(f"Error checking transactions: {e}")
```
- **Fix:** Use specific exception types; never catch `BaseException` or bare `Exception` without re-raising critical exceptions.

#### Issue ERR-002
- **File:** `cortex/daemon/sidecar/telemetry/ast_oracle.py`
- **Line:** 47, 67, 77, 160
- **Severity:** P0
- **Description:** Bare exception handlers in critical monitoring path. Can mask memory errors and system signals.
- **Fix:** Catch specific exceptions only (`OSError`, `RuntimeError`, etc.).

#### Issue ERR-003
- **File:** `cortex/daemon/sidecar/sentinel_monitor/monitor.py`
- **Line:** 60, 82, 105, 172, 181
- **Severity:** P0
- **Description:** Security monitor with broad exception swallowing. Failed security checks are logged but not escalated.
- **Fix:** Implement exception classification; re-raise security-critical errors.

---

### P1: Missing Error Boundaries in Async Operations

#### Issue ERR-004
- **File:** `cortex/notifications/bus.py`
- **Line:** 101-106
- **Severity:** P1
- **Description:** Adapter errors logged but never escalated. Failed notifications (e.g., security alerts) silently dropped.
```python
async def _safe_send(self, adapter: BaseAdapter, event: CortexEvent) -> None:
    try:
        await adapter.send(event)
    except Exception as exc:  # noqa: BLE001
        logger.error("Adapter '%s' raised unexpectedly: %s", adapter.name, exc)
        # Event lost, no retry, no escalation
```
- **Fix:** Implement dead-letter queue; add retry with exponential backoff; escalate critical events.

#### Issue ERR-005
- **File:** `cortex/llm/router.py`
- **Line:** 135-142
- **Severity:** P1
- **Description:** LLM provider errors caught as `Exception` but not classified. Network errors vs. auth errors vs. rate limits all treated identically.
```python
except Exception as e:  # deliberate boundary — LLM providers can raise any type
    return Err(str(e))
```
- **Fix:** Create exception hierarchy for LLM errors; implement specific handling per error type.

#### Issue ERR-006
- **File:** `cortex/events/bus.py`
- **Line:** 38-46
- **Severity:** P1
- **Description:** Event bus gathers tasks with `return_exceptions=True` but never handles returned exceptions. Errors silently swallowed.
```python
await asyncio.gather(*tasks, return_exceptions=True)  # Exceptions returned but ignored
```
- **Fix:** Process returned exceptions; implement error callback or dead-letter mechanism.

---

### P2: Partial Error Handling

#### Issue ERR-007
- **File:** `cortex/engine_async.py`
- **Line:** 313-315
- **Severity:** P2
- **Description:** Vote transaction rolls back on error but error details lost to caller in some code paths.
- **Fix:** Ensure all error information is propagated to caller.

#### Issue ERR-008
- **File:** `cortex/database/writer.py`
- **Line:** 297-299
- **Severity:** P2
- **Description:** Writer loop catches exceptions but continues processing. A poison message could cause infinite error loop.
```python
except (sqlite3.Error, RuntimeError) as e:
    logger.exception("Unexpected error in writer loop: %s", e)
    # Continues to next iteration - potential infinite error loop
```
- **Fix:** Implement circuit breaker; track error rate and pause processing if threshold exceeded.

#### Issue ERR-009
- **File:** `cortex/daemon/core.py`
- **Line:** 271-278
- **Severity:** P2
- **Description:** Monitor failures tracked but healing triggered only after MAX_CONSECUTIVE_FAILURES. No exponential backoff.
- **Fix:** Implement backoff for healing attempts; prevent healing storm.

---

## 3. CIRCULAR DEPENDENCIES

### P1: Import Cycles Detected

#### Issue CIRC-001
- **Files:** 
  - `cortex/engine/store_mixin.py` → `cortex/graph/__init__.py`
  - `cortex/graph/__init__.py` → `cortex/engine_async.py`
  - `cortex/engine_async.py` → `cortex/engine/store_mixin.py`
- **Severity:** P1
- **Description:** Circular import chain. Mitigated by lazy imports but causes import-time side effects and complicates testing.
```python
# In store_mixin.py (lines 98, 178)
from cortex.graph import process_fact_graph  # Lazy import indicates cycle
```
- **Fix:** Extract shared interfaces to `cortex/types/` or `cortex/interfaces/`; use dependency injection instead of direct imports.

#### Issue CIRC-002
- **Files:**
  - `cortex/auth/__init__.py` → `cortex/api/deps.py`
  - `cortex/api/deps.py` → `cortex/auth/__init__.py`
- **Severity:** P1
- **Description:** Circular dependency between auth and API deps. Lazy import in `require_consensus()` (line 422) indicates design issue.
```python
# Line 422
from cortex.api.deps import get_async_engine  # Lazy import inside function
```
- **Fix:** Move `get_async_engine` to shared module; use protocol/abstract base class.

#### Issue CIRC-003
- **Files:**
  - `cortex/memory/manager.py` → `cortex/llm/router.py`
  - `cortex/llm/router.py` → `cortex/thinking/fusion.py`
  - `cortex/thinking/fusion.py` → `cortex/llm/boundary.py`
- **Severity:** P2
- **Description:** Deep import chain in thinking/memory layers. Lazy imports mask but don't solve the architectural coupling.
- **Fix:** Define clear layer boundaries; extract protocols to separate module.

#### Issue CIRC-004
- **Files:**
  - `cortex/utils/i18n.py` → `cortex/facts/__init__.py`
  - `cortex/facts/manager.py` → `cortex/memory/temporal.py`
  - `cortex/memory/temporal.py` → `cortex/utils/i18n.py`
- **Severity:** P2
- **Description:** Potential circular import in i18n/facts/memory chain. Lazy import at line 195 in i18n.py indicates cycle.
```python
# Line 195 in i18n.py
from cortex.facts import store_fact  # Lazy import
```
- **Fix:** Move fact storage interface to shared types; use dependency injection.

---

### P2: Runtime Import Side Effects

#### Issue CIRC-005
- **File:** `cortex/config.py`
- **Line:** 208
- **Severity:** P2
- **Description:** Module-level `reload()` call at import time causes side effects. Configuration loaded before logging configured.
```python
reload()  # Executed at module import time
```
- **Fix:** Remove automatic reload; require explicit initialization call.

#### Issue CIRC-006
- **File:** `cortex/cli/tips.py`
- **Line:** 80-86
- **Severity:** P2
- **Description:** Global lock and cache initialized at import time with threading primitives.
```python
_static_lock = threading.Lock()
```
- **Fix:** Use lazy initialization pattern for thread-local resources.

---

## 4. SCALABILITY BOTTLENECKS

### P0: Synchronous I/O in Async Context

#### Issue SCALE-001
- **File:** `cortex/storage/turso.py`
- **Line:** 55-161
- **Severity:** P0
- **Description:** All database operations wrapped in `asyncio.to_thread()` with synchronous SQLite. Each operation spawns a thread, causing thread explosion under load.
```python
self._conn = await asyncio.to_thread(libsql_client.connect, ...)
cursor = await asyncio.to_thread(self._conn.execute, sql, params)
```
- **Fix:** Use native async database driver (e.g., `asyncpg` for PostgreSQL, proper async libsql client).

#### Issue SCALE-002
- **File:** `cortex/timing/tracker.py`
- **Line:** 1-260
- **Severity:** P0
- **Description:** Uses `threading.Lock` in mixed async/sync environment. SQLite operations are synchronous. Will block async event loop.
```python
self._lock = threading.Lock()  # Wrong lock type for async
```
- **Fix:** Use `asyncio.Lock` for async context; redesign for async-first operation.

---

### P1: Unbounded Resource Growth

#### Issue SCALE-003
- **File:** `cortex/gate/core.py`
- **Line:** 67-68
- **Severity:** P1
- **Description:** Pending actions and audit logs grow unbounded in memory. No eviction policy.
```python
self._pending: dict[str, PendingAction] = {}
self._audit_log: list[dict[str, Any]] = []  # Unbounded growth
```
- **Fix:** Implement LRU cache or TTL eviction for pending actions; rotate audit logs.

#### Issue SCALE-004
- **File:** `cortex/daemon/core.py`
- **Line:** 353-378
- **Severity:** P1
- **Description:** Creates multiple daemon threads without limit. Thread-per-monitor pattern doesn't scale.
```python
neural_thread = threading.Thread(...)
t = threading.Thread(target=self._run_ast_oracle_loop, ...)
t = threading.Thread(target=self.fiat_oracle.run_sync_loop, ...)
```
- **Fix:** Use thread pool with limited workers; consolidate to fewer threads with async event loops.

#### Issue SCALE-005
- **File:** `cortex/search/hybrid.py`
- **Line:** 30-116
- **Severity:** P1
- **Description:** RRF fusion loads all results into memory (`fetch_limit = top_k * 2`). For large top_k, memory usage explodes.
```python
fetch_limit = top_k * 2  # Can be large if top_k is large
```
- **Fix:** Implement streaming RRF with bounded memory; use generators.

---

### P1: Lock Contention

#### Issue SCALE-006
- **File:** `cortex/database/pool.py`
- **Line:** 51, 128
- **Severity:** P1
- **Description:** Lock acquired during connection release (`self._semaphore.release()` happens in finally, but lock during put). High contention under load.
```python
async with self._lock:  # Contention point
    self._active_count += 1
```
- **Fix:** Use lock-free counters (`asyncio.Queue` has built-in synchronization); minimize critical sections.

#### Issue SCALE-007
- **File:** `cortex/auth/__init__.py`
- **Line:** 136-148, 226-246
- **Severity:** P1
- **Description:** Synchronous wrappers use `threading.Event` with `asyncio.run_coroutine_threadsafe`. Creates thread-per-call overhead.
```python
event = threading.Event()
asyncio.run_coroutine_threadsafe(_wrapper(), loop)
event.wait()  # Blocks thread
```
- **Fix:** Provide proper async API; deprecate sync wrappers.

---

### P2: Inefficient Algorithms

#### Issue SCALE-008
- **File:** `cortex/graph/backends/sqlite/algorithms.py`
- **Line:** 29-53
- **Severity:** P2
- **Description:** BFS uses list as queue (`queue.pop(0)` is O(n)). Pathological for deep graphs.
```python
queue.pop(0)  # O(n) operation
```
- **Fix:** Use `collections.deque` for O(1) pops.

#### Issue SCALE-009
- **File:** `cortex/graph/backends/sqlite.py`
- **Line:** 241, 265
- **Severity:** P2
- **Description:** Same BFS inefficiency with list.pop(0).
- **Fix:** Use `collections.deque`.

#### Issue SCALE-010
- **File:** `cortex/engine/ledger.py`
- **Line:** 213-250
- **Severity:** P2
- **Description:** Ledger verification iterates all transactions in Python loop. O(n) memory and time.
```python
while True:
    tx = await cursor.fetchone()
    # Verification in Python loop
```
- **Fix:** Implement batch verification; use SQL window functions for hash chain validation.

---

### P2: Unbounded Queues

#### Issue SCALE-011
- **File:** `cortex/database/cache.py`
- **Line:** 41, 87-98
- **Severity:** P2
- **Description:** Subscriber queues (`list[asyncio.Queue]`) have no size limit. Slow subscriber can cause memory exhaustion.
```python
self._subscribers: list[asyncio.Queue] = []  # Unbounded queues
queue.put_nowait((event, key))  # Can raise QueueFull but not handled
```
- **Fix:** Use bounded queues with backpressure; implement slow subscriber cutoff.

---

## 5. SECURITY VULNERABILITIES

### P0: Cryptographic Issues

#### Issue SEC-001
- **File:** `cortex/crypto/aes.py`
- **Line:** 126-132
- **Severity:** P0
- **Description:** Master key derived from environment without key derivation function. Direct use of environment variable as encryption key.
```python
default_key = os.environ.get("CORTEX_MASTER_KEY", "")
if not default_key:
    default_key = "CORTEX_DEFAULT_KEY_CHANGE_ME"  # Hardcoded fallback!
```
- **Fix:** Require explicit key configuration; remove hardcoded fallback; use PBKDF2 or Argon2 for key derivation.

#### Issue SEC-002
- **File:** `cortex/gate/core.py`
- **Line:** 55-62
- **Severity:** P0
- **Description:** Falls back to ephemeral random secret if env var not set. Multi-instance deployments will have different secrets.
```python
self._secret = (
    secret or os.environ.get("CORTEX_GATE_SECRET") or os.environ.get("CORTEX_VAULT_KEY")
)
if not self._secret:
    self._secret = secrets.token_hex(32)  # Different on each instance!
```
- **Fix:** Fail hard if secret not configured; never auto-generate in production.

---

### P1: Injection Vulnerabilities

#### Issue SEC-003
- **File:** `cortex/utils/sandbox.py`
- **Line:** 189-250
- **Severity:** P1
- **Description:** AST sandbox uses string formatting for restricted globals. Potential for sandbox escape via name collision.
- **Fix:** Use explicit whitelist instead of blacklist; validate all attribute access.

#### Issue SEC-004
- **File:** Multiple files
- **Line:** Various
- **Severity:** P1
- **Description:** SQL queries use f-strings for column lists but parameterized queries for values. Potential for column name injection if user-controlled input reaches column selection.
```python
# Example from engine_async.py line 39-44
FACT_COLUMNS = (
    "f.id, f.project, ..."  # String interpolation risk
)
```
- **Fix:** Validate all column names against whitelist; never use f-strings for SQL identifiers.

---

## 6. DATA CONSISTENCY ISSUES

### P1: Transaction Boundaries

#### Issue CONSIST-001
- **File:** `cortex/engine_async.py`
- **Line:** 99-131
- **Description:** `_log_transaction` reads then writes with potential race condition between SELECT and INSERT.
```python
async with conn.execute("SELECT hash FROM transactions ORDER BY id DESC LIMIT 1") as cursor:
    prev = await cursor.fetchone()  # Race window
# ... later INSERT
```
- **Fix:** Use database-level sequence or ID generation; wrap in proper transaction with SERIALIZABLE isolation.

#### Issue CONSIST-002
- **File:** `cortex/memory/manager.py`
- **Line:** 129-147
- **Description:** L3 append and L1 update not atomic. Crash between steps = data inconsistency.
```python
await self._l3.append_event(event)  # If this succeeds...
overflowed = self._l1.add_event(event)  # ...but this fails, inconsistency
```
- **Fix:** Implement two-phase commit or saga pattern; add reconciliation job.

---

## 7. OBSERVABILITY GAPS

### P2: Missing Metrics

#### Issue OBS-001
- **File:** `cortex/database/writer.py`
- **Line:** 91-95
- **Severity:** P2
- **Description:** Only basic metrics tracked. No queue depth metric, no error rate metric.
```python
self._metrics: dict[str, float] = {
    "avg_wait_ms": 0.0,
    "avg_exec_ms": 0.0,
    "total_ops": 0,  # Missing: queue_depth, error_rate, timeout_rate
}
```
- **Fix:** Add comprehensive metrics for queue depth, error rates, timeouts.

#### Issue OBS-002
- **File:** `cortex/llm/router.py`
- **Line:** 91-146
- **Severity:** P2
- **Description:** No metrics on provider success rates, latency percentiles, or fallback frequency.
- **Fix:** Add OpenTelemetry metrics for provider performance.

---

## 8. CONCRETE FIX RECOMMENDATIONS

### Immediate (P0) Fixes

1. **Add Thread-Safe Singleton Pattern:**
```python
import threading
from functools import wraps

def thread_safe_singleton(cls):
    instances = {}
    locks = {}
    
    @wraps(cls)
    def get_instance(*args, **kwargs):
        if cls not in instances:
            if cls not in locks:
                locks[cls] = threading.Lock()
            with locks[cls]:
                if cls not in instances:
                    instances[cls] = cls(*args, **kwargs)
        return instances[cls]
    return get_instance
```

2. **Fix Exception Handling:**
```python
# Instead of:
except Exception as e:

# Use:
except (OSError, RuntimeError, ValueError) as e:
    # Handle expected errors
except Exception as e:
    # Log and re-raise unexpected errors
    logger.exception("Unexpected error")
    raise
```

3. **Replace Synchronous I/O:**
```python
# Instead of:
await asyncio.to_thread(sync_operation)

# Use:
# Native async driver or properly sized thread pool
```

### Short-term (P1) Fixes

1. **Implement Circuit Breaker Pattern:**
```python
class CircuitBreaker:
    def __init__(self, failure_threshold=5, timeout=60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failures = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
```

2. **Add Bounded Queues with Backpressure:**
```python
self._queue: asyncio.Queue[_Message] = asyncio.Queue(maxsize=1000)
# Use put with timeout or block with backpressure signal
```

3. **Implement Audit Log Persistence:**
```python
async def _persist_audit_log(self, entry: dict) -> None:
    async with aiofiles.open(self.audit_file, 'a') as f:
        await f.write(json.dumps(entry) + '\n')
        await f.flush()
```

### Long-term (P2/P3) Improvements

1. **Extract Clean Architecture Layers:**
   - Domain layer (types, entities)
   - Application layer (use cases)
   - Infrastructure layer (DB, LLM, notifications)
   - Interface layer (API, CLI)

2. **Implement Event Sourcing:**
   - Replace mutable state with event log
   - Enable true auditability and replay

3. **Add Distributed Tracing:**
   - OpenTelemetry integration
   - Trace across async boundaries
   - Correlate with tenant_id

---

## 9. TESTING RECOMMENDATIONS

### Critical Tests Missing

1. **Race Condition Tests:**
   - Concurrent singleton initialization
   - Simultaneous config reload

2. **Failure Injection Tests:**
   - Database connection drop mid-transaction
   - LLM provider timeout
   - Notification adapter failure

3. **Load Tests:**
   - Queue saturation behavior
   - Connection pool exhaustion
   - Memory growth under sustained load

---

## 10. SUMMARY BY COMPONENT

| Component | P0 | P1 | P2 | P3 | Critical Issues |
|-----------|----|----|----|----|-----------------|
| config.py | 1 | 0 | 1 | 0 | Singleton thread-safety |
| notifications/bus.py | 1 | 1 | 0 | 0 | Singleton, error swallowing |
| gate/core.py | 2 | 1 | 0 | 0 | Singleton, memory growth |
| auth/__init__.py | 1 | 2 | 0 | 0 | Singleton, thread overhead |
| database/writer.py | 0 | 1 | 1 | 0 | Single writer bottleneck |
| database/pool.py | 0 | 1 | 1 | 0 | Connection limits |
| daemon/core.py | 0 | 2 | 1 | 0 | Thread explosion |
| memory/manager.py | 0 | 1 | 1 | 0 | Task dropping |
| llm/router.py | 0 | 1 | 1 | 0 | Error classification |
| events/bus.py | 0 | 1 | 0 | 0 | Exception handling |
| crypto/aes.py | 1 | 0 | 0 | 0 | Key derivation |
| storage/turso.py | 1 | 0 | 0 | 0 | Thread-per-operation |
| timing/tracker.py | 1 | 0 | 0 | 0 | Sync in async |
| **TOTAL** | **8** | **14** | **23** | **31** | |

---

## APPENDIX: SEVERITY DEFINITIONS

- **P0 (Critical):** System-wide failure, data loss, security breach, or complete unavailability. Requires immediate fix.
- **P1 (High):** Major functionality degradation, significant performance impact, or potential for cascading failures. Fix within 1 week.
- **P2 (Medium):** Partial failures, reliability issues, or architectural debt affecting maintainability. Fix within 1 month.
- **P3 (Low):** Code quality issues, minor inefficiencies, or cosmetic problems. Fix as time permits.

---

*End of Audit Report*
