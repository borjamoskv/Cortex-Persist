import re

with open('cortex/database/core.py') as f:
    content = f.read()

new_content = re.sub(
    r'import sqlite3',
    'import sqlite3\nimport uuid\nimport secrets\nimport os',
    content,
    count=1
)

# Remove ContextVar
new_content = re.sub(
    r'# \[Nivel 20\].*?CORTEX_CAUSAL_WRITE_AUTHORIZED = contextvars\.ContextVar\("cortex_causal_write_authorized", default=False\)',
    '',
    new_content,
    flags=re.DOTALL
)

# Remove old authorizer and connect hook
old_hook_pattern = r'def _physical_authorizer.*?sqlite3\.connect = _secure_sqlite3_connect'
new_hook = '''class CortexConnection(sqlite3.Connection):
    """
    [C5-REAL] State-Bound Connection Kernel.
    Token and authority are physically bound to the connection state,
    annihilating ContextVar drift and Thread pool leaks.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._connection_id = uuid.uuid4().hex
        self._mtk_nonce = secrets.token_hex(16)
        self._causal_write_authorized = False
        
        # Inyectar el authorizer atado al estado físico de esta conexión
        self.set_authorizer(self._physical_authorizer_bound)
        
        # Engine Lockdown - Cerrar superficie VFS y PRAGMA
        self.execute("PRAGMA trusted_schema = OFF")
        self.execute("PRAGMA writable_schema = OFF")
        self.execute("PRAGMA cell_size_check = ON")
        # Antigravity-2 C5-REAL Homeostasis: Prevención de Deadlocks y Corrupción
        self.execute("PRAGMA journal_mode = WAL")
        self.execute("PRAGMA busy_timeout = 5000")
        self.execute("PRAGMA synchronous = NORMAL")
        
        if hasattr(self, "enable_load_extension"):
            self.enable_load_extension(False)
            
    def _physical_authorizer_bound(self, action: int, table: str | None, column: str | None, sql_location: str | None, ignore: str | None) -> int:
        if action in (sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE):
            if table and table.startswith("sqlite_"):
                return sqlite3.SQLITE_OK
            
            if not self._causal_write_authorized:
                return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK
        
    def authorize_causal_writes(self) -> str:
        """Grants causal write authority to this specific handle."""
        self._causal_write_authorized = True
        return self._mtk_nonce

    def revoke_causal_writes(self) -> None:
        self._causal_write_authorized = False

_original_sqlite3_connect = sqlite3.connect

def _secure_sqlite3_connect(*args, **kwargs):
    """
    [C5-REAL] Kernel-owned Connection Allocator Hook.
    Blocks any raw sqlite3.connect() calls that do not use the CortexConnection factory.
    """
    factory = kwargs.get("factory")
    if factory is not CortexConnection:
        raise RuntimeError("[C5-REAL] FATAL: Direct sqlite3.connect() is structurally forbidden. Use MTK Allocator (cortex.database.core.connect).")
    return _original_sqlite3_connect(*args, **kwargs)

sqlite3.connect = _secure_sqlite3_connect'''

new_content = re.sub(old_hook_pattern, new_hook, new_content, flags=re.DOTALL)

# Add factory=CortexConnection to connect
new_content = re.sub(
    r'conn = sqlite3\.connect\(\s*db_path,\s*timeout=timeout,\s*check_same_thread=check_same_thread,\s*uri=uri,\s*isolation_level=isolation_level,\s*# type: ignore\[type-error\]\s*\)',
    'conn = sqlite3.connect(\n            db_path,\n            timeout=timeout,\n            check_same_thread=check_same_thread,\n            uri=uri,\n            isolation_level=isolation_level,  # type: ignore[type-error]\n            factory=CortexConnection,\n        )',
    new_content,
    flags=re.DOTALL
)

# Add factory=CortexConnection to connect_writer
new_content = re.sub(
    r'conn = sqlite3\.connect\(\s*db_path,\s*timeout=timeout,\s*check_same_thread=check_same_thread,\s*uri=uri,\s*\)',
    'conn = sqlite3.connect(\n            db_path,\n            timeout=timeout,\n            check_same_thread=check_same_thread,\n            uri=uri,\n            factory=CortexConnection,\n        )',
    new_content,
    flags=re.DOTALL
)

# Add factory=CortexConnection to connect_async
new_content = re.sub(
    r'conn = await aiosqlite\.connect\(db_path, timeout=5\.0, uri=is_uri\)',
    'conn = await aiosqlite.connect(db_path, timeout=5.0, uri=is_uri, factory=CortexConnection)',
    new_content,
    flags=re.DOTALL
)

# Add CortexConnection to __all__
new_content = new_content.replace('"CORTEX_CAUSAL_WRITE_AUTHORIZED",', '"CortexConnection",')

with open('cortex/database/core.py', 'w') as f:
    f.write(new_content)
