
with open("cortex/database/pool.py") as f:
    code = f.read()

# 1. Remove threading import if not needed elsewhere
# threading is only used for threading.local()
code = code.replace("import threading\n", "")

# 2. Add dataclass for PoolState
pool_state_class = """class _PoolState:
    def __init__(self, max_connections: int):
        self.pool: asyncio.Queue[aiosqlite.Connection] = asyncio.Queue()
        self.active_count: int = 0
        self.lock = asyncio.Lock()
        self.semaphore = asyncio.Semaphore(max_connections)
        self.initialized: bool = False

"""
code = code.replace("class CortexConnectionPool:", pool_state_class + "class CortexConnectionPool:")

# 3. Modify __init__
init_target = """        self.chaos_gate = ChaosGate(name=f"sqlite_pool:{self.db_path}")
        self._local = threading.local()

    def _get_local_state(self):
        \"\"\"Get or initialize thread-local pool state.\"\"\"
        if not hasattr(self._local, "pool"):
            self._local.pool = asyncio.Queue()
            self._local.active_count = 0
            self._local.lock = asyncio.Lock()
            self._local.semaphore = asyncio.Semaphore(self.max_connections)
            self._local.initialized = False
        return self._local"""
init_replace = """        self.chaos_gate = ChaosGate(name=f"sqlite_pool:{self.db_path}")
        self._state: _PoolState | None = None

    def _get_state(self) -> _PoolState:
        \"\"\"Get or initialize pool state tied to the current event loop.\"\"\"
        if self._state is None:
            self._state = _PoolState(self.max_connections)
        return self._state"""
code = code.replace(init_target, init_replace)

# 4. Replace _get_local_state() with _get_state()
code = code.replace("self._get_local_state()", "self._get_state()")

with open("cortex/database/pool.py", "w") as f:
    f.write(code)
print("pool.py successfully refactored")
