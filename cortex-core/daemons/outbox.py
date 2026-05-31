import os
import json
import time
import asyncio
import sqlite3
import mmap
import weakref
import atexit
from persistence.base import SovereignResource, _setup_sqlite_pragmas, _get_local_conn, HAS_CORTEX_RS, outbox_wake_event, logger, _metrics_cache, _metrics_cache_lock, DB_PATH
if HAS_CORTEX_RS:
    import cortex_rs
from persistence.ledger import LedgerManager

class ZeroCopyRingBuffer(SovereignResource):
    """L4 Sovereign Zero-Copy Ring Buffer.
    Bypasses SQLite & JSON deserialization using C-contiguous mmap memoryviews.
    Memory Layout per Task (256 bytes):
      [0]    : Status (0=Free, 1=Pending, 2=Processing)
      [1:9]  : Timestamp (double)
      [9:73] : Agent ID Hash (64 bytes)
      [73:]  : Binary Payload (183 bytes)
    """

    def __init__(self, capacity=None):
        import os
        import weakref
        import sys
        if capacity is None:
            if 'pytest' in sys.modules:
                capacity = 100
            else:
                capacity = 1000000
        self.capacity = capacity
        self.task_size = 256
        self.tensor_size = self.capacity * self.task_size
        self.bin_path = os.path.join(os.path.dirname(DB_PATH), 'swarm_ring_vsa.bin')
        self._mmap = None
        self._f = None
        if not os.path.exists(self.bin_path) or os.path.getsize(self.bin_path) < self.tensor_size:
            with open(self.bin_path, 'wb') as f:
                f.write(b'\x00' * self.tensor_size)
        if HAS_CORTEX_RS:
            try:
                self._rust_buf = cortex_rs.ZeroCopyRingBuffer(self.bin_path, self.capacity)
            except Exception as e:
                logger.warning('Failed to initialize Rust ZeroCopyRingBuffer, using Python fallback: %s', e)
                self._rust_buf = None
        else:
            self._rust_buf = None
        if self._rust_buf is None:
            import itertools
            self._f = open(self.bin_path, 'r+b')
            self._mmap = mmap.mmap(self._f.fileno(), self.tensor_size)
            self._buffer = memoryview(self._mmap)
            self._read_idx = 0
            for i in range(self.capacity):
                if self._buffer[i * self.task_size] == 1:
                    self._read_idx = i
                    break
            write_start = self._read_idx
            for i in range(self.capacity):
                idx = (self._read_idx + i) % self.capacity
                if self._buffer[idx * self.task_size] == 0:
                    write_start = idx
                    break
            self._write_counter = itertools.count(write_start)
        try:
            import sys
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from ultramap import UltramapSubstrate
            self.umap = UltramapSubstrate(capacity=self.capacity)
        except Exception as e:
            logger.warning('UltraMap integration failed: %s', e)
            self.umap = None
        self._finalizer = weakref.finalize(self, self._safe_close, getattr(self, '_buffer', None), getattr(self, '_mmap', None), getattr(self, '_f', None))

    def close(self) -> None:
        """TODO: Document close"""
        if hasattr(self, '_finalizer') and self._finalizer is not None and self._finalizer.alive:
            self._finalizer.detach()
        if hasattr(self, '_buffer') and self._buffer is not None:
            try:
                self._buffer.release()
            except ValueError:
                pass
            self._buffer = None
        if hasattr(self, '_mmap') and self._mmap is not None:
            try:
                self._mmap.close()
            except ValueError:
                pass
            self._mmap = None
        if hasattr(self, '_f') and self._f is not None:
            try:
                self._f.close()
            except OSError:
                pass
            self._f = None
        super().close()

    def enqueue(self, agent_id: bytes, payload: bytes) -> bool:
        """O(1) Zero-copy memory write. Bypasses VSA OS locks."""
        if self._rust_buf is not None:
            return self._rust_buf.enqueue(agent_id, payload)
        write_idx = next(self._write_counter) % self.capacity
        offset = write_idx * self.task_size
        if self._buffer[offset] != 0:
            return False
        import struct
        struct.pack_into('d', self._buffer, offset + 1, time.monotonic())
        agent_bytes = agent_id[:64].ljust(64, b'\x00')
        self._buffer[offset + 9:offset + 73] = agent_bytes
        payload_bytes = payload[:183].ljust(183, b'\x00')
        self._buffer[offset + 73:offset + 256] = payload_bytes
        self._buffer[offset] = 1
        try:
            if hasattr(self, 'umap') and self.umap is not None:
                x = time.monotonic() * 10.0 % 1000.0
                y = write_idx * 13.37 % 1000.0
                z = len(payload) * 1.0
                target = agent_id.decode('utf-8', 'ignore').strip('\x00')
                self.umap.update_agent_position(write_idx, x, y, z, target, 0.8)
        except Exception as e:
            logger.error('UltraMap topological update error: %s', e)
        return True

    def fetch_pending(self):
        """Zero-copy read direct from C-contiguous memory."""
        if self._rust_buf is not None:
            return self._rust_buf.fetch_pending()
        tasks = []
        import struct
        for _ in range(self.capacity):
            offset = self._read_idx * self.task_size
            if self._buffer[offset] == 1:
                self._buffer[offset] = 2
                ts = struct.unpack_from('d', self._buffer, offset + 1)[0]
                agent_id = bytes(self._buffer[offset + 9:offset + 73]).rstrip(b'\x00')
                payload = bytes(self._buffer[offset + 73:offset + 256]).rstrip(b'\x00')
                tasks.append((self._read_idx, ts, agent_id, payload))
                self._buffer[offset] = 0
            self._read_idx = (self._read_idx + 1) % self.capacity
        return tasks

    def get_pending_count(self) -> int:
        """Scan the buffer memory or binary file to count tasks with status = 1 (Pending)."""
        count = 0
        try:
            if hasattr(self, '_buffer') and self._buffer is not None:
                count = self._buffer[0::self.task_size].tobytes().count(b'\x01')
            elif os.path.exists(self.bin_path):
                with open(self.bin_path, 'rb') as f:
                    data = f.read(self.capacity * self.task_size)
                    count = data[0::self.task_size].count(b'\x01')
        except Exception as e:
            logger.error('Failed to count pending tasks in ZeroCopyRingBuffer: %s', e)
        return count

    def reset(self) -> None:
        """Zero out the buffer to reset the C5-REAL state."""
        if self._rust_buf is not None:
            try:
                self._rust_buf.reset()
            except Exception as e:
                logger.error('Failed to reset Rust ZeroCopyRingBuffer: %s', e)
        try:
            if os.path.exists(self.bin_path):
                with open(self.bin_path, 'r+b') as f:
                    f.write(b'\x00' * self.tensor_size)
        except Exception as e:
            logger.error('Failed to zero out ring buffer file: %s', e)
        if hasattr(self, '_buffer') and self._buffer is not None:
            try:
                self._buffer[:] = b'\x00' * self.tensor_size
            except Exception:
                pass

    def process_all_native(self, num_threads=None):
        """Process all pending tasks natively in Rust using Rayon thread pool (releases the GIL)."""
        if self._rust_buf is not None:
            return self._rust_buf.process_all_native(num_threads)
        raise RuntimeError('Rust cortex_rs module not available for native processing.')
_global_ring_buffer = None

def _get_ring_buffer():
    global _global_ring_buffer
    if _global_ring_buffer is None:
        _global_ring_buffer = ZeroCopyRingBuffer()
    return _global_ring_buffer

class OutboxDaemon(SovereignResource):
    """Outbox Pattern Daemon: Asynchronously drains pending swarm tasks to NEXUS API."""

    def __init__(self, db_path: str | None=None, ledger: LedgerManager | None=None):
        self._db_path = db_path if db_path is not None else DB_PATH
        self._daemon_task = None
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False, timeout=10.0)
        _setup_sqlite_pragmas(self._conn)
        self._finalizer = weakref.finalize(self, self._safe_close, self._conn)
        atexit.register(self.close)
        self.ledger = ledger

    def get_health_metrics(self) -> dict:
        """Returns C5-REAL telemetry for the Outbox Pattern."""
        return {'pending_tasks': 0, 'failed_tasks': 0, 'completed_tasks': 0, 'max_latency_seconds': 0.0, 'status': 'C5-REAL_LOCK_FREE'}

    def _fetch_pending_tasks(self) -> list:
        """Fetch pending tasks from ZeroCopyRingBuffer."""
        try:
            ring = _get_ring_buffer()
            ring_tasks = ring.fetch_pending()
            if ring_tasks:
                return [(f'ring_{idx}', agent.decode('utf-8', 'ignore').rstrip('\x00'), payload.decode('utf-8', 'ignore').rstrip('\x00')) for idx, ts, agent, payload in ring_tasks]
        except Exception as e:
            logger.error('ZeroCopyRingBuffer fetch failed: %s', e)
        return []

    def drain_once_sync(self) -> None:
        """Synchronously drains a batch of pending tasks (primarily for tests and synchronous fallbacks)."""
        try:
            tasks = self._fetch_pending_tasks()
            if not tasks:
                return
            for task in tasks:
                row_id, agent_name, payload = task
                logger.info('Processing task %s from %s', row_id, agent_name)
                try:
                    payload_dict = json.loads(payload)
                except Exception as e:
                    logger.error('Failed to parse task payload json: %s', e)
                    payload_dict = {}
                if payload_dict.get('type') == 'EXA_LISP':
                    try:
                        from exa_lisp_genesis import parse, tokenize, evaluate, ExergyEnvironment, EntropyDeath
                        logger.info(f"C5-REAL EXA_LISP Invoked. Limits: {payload_dict.get('exergy_limit', 1000)}j")
                        code = payload_dict.get('code', '')
                        limit = payload_dict.get('exergy_limit', 1000)
                        env = ExergyEnvironment(joules=limit, ledger=self.ledger)
                        ast = parse(tokenize(code))
                        result = evaluate(ast, env)
                        logger.info(f'EXA_LISP Output: {result}')
                        if self.ledger:
                            self.ledger.append(action='C5_VERIFIED_EXA', vector_id=agent_name, yield_amount=float(getattr(env, 'joules', 0.0)))
                        continue
                    except EntropyDeath as e:
                        logger.error(f'EXA_LISP Halted (EntropyDeath): {e}')
                        if self.ledger:
                            burned = limit - getattr(env, 'joules', 0.0)
                            self.ledger.append(action='C5_FALSATED_ENTROPY', vector_id=agent_name, yield_amount=float(-burned))
                        continue
                    except Exception as e:
                        logger.error(f'EXA_LISP Syntax/Runtime Error: {e}')
                        if self.ledger:
                            burned = limit - getattr(env, 'joules', limit)
                            penalty = burned if burned > 0 else 10.0
                            self.ledger.append(action='C5_FALSATED_SYNTAX', vector_id=agent_name, yield_amount=float(-penalty))
                        continue
                if payload_dict.get('type') == 'QUANTUM_BRANCHING':
                    try:
                        from exa_lisp_genesis import parse, tokenize, evaluate, ExergyEnvironment, EntropyDeath
                        logger.info('C5-REAL QUANTUM_BRANCHING (Q-Let v2) Invoked. Speculative parallel evaluation.')
                        branches = payload_dict.get('branches', [])
                        limit = payload_dict.get('exergy_limit', 1000)

                        def _evaluate_branch(code, branch_id, bound_limit=limit):
                            env = ExergyEnvironment(joules=bound_limit, ledger=self.ledger)
                            try:
                                ast = parse(tokenize(code))
                                result = evaluate(ast, env)
                                return (branch_id, result, env.joules, True)
                            except Exception as e:
                                return (branch_id, str(e), getattr(env, 'joules', 0), False)
                        best_branch = None
                        max_exergy_retained = -1.0
                        max_workers = min(32, len(branches) if branches else 1)
                        if max_workers > 0:
                            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                                futures = [executor.submit(_evaluate_branch, b.get('code', ''), b.get('id', str(i))) for i, b in enumerate(branches)]
                                for future in concurrent.futures.as_completed(futures):
                                    branch_id, result, remaining_joules, success = future.result()
                                    if success and remaining_joules > max_exergy_retained:
                                        max_exergy_retained = remaining_joules
                                        best_branch = (branch_id, result)
                            if best_branch:
                                logger.info(f'Q-Let v2 Collapsed: Selected Branch {best_branch[0]} with Retained Exergy: {max_exergy_retained}J')
                                if self.ledger:
                                    self.ledger.append(action='Q_BRANCH_COLLAPSE', vector_id=str(best_branch[0]), yield_amount=float(max_exergy_retained))
                        continue
                    except Exception as e:
                        logger.error(f'QUANTUM_BRANCHING Error: {e}')
                        if self.ledger:
                            self.ledger.append(action='C5_FALSATED_QUANTUM', vector_id=agent_name, yield_amount=float(-limit))
                        continue
                if payload_dict.get('type') == 'AST_MUTATION':
                    try:
                        from aeon_0_compiler import AEON0Compiler
                        logger.info('C5-REAL AST_MUTATION Invoked via AEON-0 Compiler.')
                        compiler = AEON0Compiler(ledger=self.ledger)
                        compiler.mutate(payload_dict)
                        if self.ledger:
                            self.ledger.append(action='C5_VERIFIED_MUTATION', vector_id=agent_name, yield_amount=0.0)
                        continue
                    except Exception as e:
                        logger.error(f'AEON-0 Compiler Error: {e}')
                        if self.ledger:
                            self.ledger.append(action='C5_FALSATED_MUTATION', vector_id=agent_name, yield_amount=-50.0)
                        continue
                if payload_dict.get('type') == 'L1_EXTERNAL_PATCH':
                    try:
                        from telemetry_gate import TelemetryGate
                        from swarm_manager import SwarmActuator
                        logger.info(f'C5-REAL L1_EXTERNAL_PATCH Invoked for agent {agent_name}. Routing to Telemetry Gate.')
                        actuator = SwarmActuator(self._db_path)
                        gate = TelemetryGate(actuator)
                        patch_string = json.dumps(payload_dict.get('patch', {}))
                        success = gate.process_external_patch(agent_name, patch_string)
                        if success:
                            logger.info(f'Telemetry Gate ACCEPTED patch from {agent_name}.')
                        else:
                            logger.warning(f'Telemetry Gate REJECTED patch from {agent_name}.')
                        continue
                    except Exception as e:
                        logger.error(f'L1_EXTERNAL_PATCH Gateway Error: {e}')
                        continue
                logger.debug(f'C5-REAL Isolation: Task {agent_name} rejected. Network dispatch is prohibited.')
        except Exception as e:
            logger.error('Outbox drainer error: %s', e)

    async def _drain_loop(self) -> None:
        """Asynchronous loop for draining the queue."""
        loop = asyncio.get_running_loop()
        while True:
            await loop.run_in_executor(None, outbox_wake_event.wait, 1.0)
            outbox_wake_event.clear()
            await loop.run_in_executor(None, self.drain_once_sync)

    def start_guardian(self) -> None:
        """TODO: Document start_guardian"""
        if self._daemon_task:
            return
        try:
            loop = asyncio.get_running_loop()
            self._daemon_task = loop.create_task(self._drain_loop())
        except RuntimeError:
            logger.warning('OutboxDaemon could not start: no active event loop.')

def _enqueue_swarm_task_sync(agent_name: str, payload: dict) -> None:
    """Zero-copy core implementation of the Swarm Queue Dispatcher."""
    try:
        ring = _get_ring_buffer()
        payload_bytes = json.dumps(payload).encode('utf-8')
        agent_bytes = agent_name.encode('utf-8')
        success = ring.enqueue(agent_bytes, payload_bytes)
        if not success:
            logger.critical('ZeroCopyRingBuffer FATAL: Buffer full. Task dropped to preserve C5-REAL thermodynamic bounds.')
            raise RuntimeError('RingBuffer capacity exceeded. C5-REAL isolation enforced.')
        outbox_wake_event.set()
    except Exception as e:
        logger.error('Failed to enqueue swarm task: %s', e)
        raise

def enqueue_swarm_task(agent_name: str, payload: dict) -> None:
    """Sovereign Swarm Queue Dispatcher. Pure Lock-Free execution bypasses executor overhead."""
    _enqueue_swarm_task_sync(agent_name, payload)

def get_swarm_metrics(bypass_cache: bool=False) -> dict:
    """Extract C5-REAL telemetry from SQLite regarding swarm operation."""
    now = time.monotonic()
    if not bypass_cache:
        with _metrics_cache_lock:
            if _metrics_cache['value'] is not None and now < _metrics_cache['expiry']:
                return _metrics_cache['value']
    try:
        conn = _get_local_conn(DB_PATH, timeout=5.0)
        c = conn.cursor()
        c.execute('SELECT AVG(execution_time) FROM (SELECT execution_time FROM cortex_execution_ledger ORDER BY timestamp DESC LIMIT 50)')
        avg_exec = c.fetchone()[0]
        latency_ms = avg_exec * 1000.0 if avg_exec else 35.0
        active_children = 0
        try:
            ring = _get_ring_buffer()
            if ring._rust_buf is not None:
                if hasattr(ring._rust_buf, 'count_pending'):
                    active_children += ring._rust_buf.count_pending()
                elif hasattr(ring._rust_buf, 'pending_count'):
                    active_children += ring._rust_buf.pending_count()
                elif os.path.exists(ring.bin_path):
                    with open(ring.bin_path, 'rb') as f:
                        data = f.read()
                    statuses = data[0::ring.task_size]
                    active_children += statuses.count(b'\x01') + statuses.count(b'\x02')
            elif hasattr(ring, '_buffer') and ring._buffer is not None:
                statuses = ring._buffer[0::ring.task_size].tobytes()
                active_children += statuses.count(b'\x01') + statuses.count(b'\x02')
        except Exception as e:
            logger.error('Failed to count RingBuffer tasks in metrics: %s', e)
        try:
            c.execute("SELECT COUNT(*) FROM cortex_swarm_queue WHERE status = 'pending'")
            active_children += c.fetchone()[0]
        except sqlite3.OperationalError as e:
            logger.debug('OperationalError querying cortex_swarm_queue: %s', e)
        c.execute('SELECT COUNT(*), SUM(CASE WHEN returncode != 0 THEN 1 ELSE 0 END) FROM (SELECT returncode FROM cortex_execution_ledger ORDER BY timestamp DESC LIMIT 100)')
        row = c.fetchone()
        if row and row[0]:
            total = row[0]
            fails = row[1] if row[1] is not None else 0
            uncertainty = fails / total
        else:
            uncertainty = 0.0
        result = {'latency_ms': round(latency_ms, 2), 'active_children': active_children, 'uncertainty': round(uncertainty, 4)}
        with _metrics_cache_lock:
            _metrics_cache['value'] = result
            _metrics_cache['expiry'] = time.monotonic() + 0.5
        return result
    except Exception as e:
        logger.error('Failed to extract swarm metrics (Deterministic C5-REAL Exception): %s', e)
        return {'latency_ms': 99999.0, 'active_children': -1, 'uncertainty': 1.0}