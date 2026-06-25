import os
import sys
import glob

SQLITE_PATCH = """
# --- C5-REAL BFT PATCH (R10) ---
import sqlite3 as _sqlite3_bft_orig
_orig_sqlite_connect = _sqlite3_bft_orig.connect
def _bft_sqlite_connect(*args, **kwargs):
    kwargs.setdefault('timeout', 5.0)
    conn = _orig_sqlite_connect(*args, **kwargs)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass
    return conn
_sqlite3_bft_orig.connect = _bft_sqlite_connect
# -------------------------------
"""

AIOSQLITE_PATCH = """
# --- C5-REAL BFT PATCH AIOSQLITE (R10) ---
import aiosqlite as _aiosqlite_bft_orig
_orig_aiosqlite_connect = _aiosqlite_bft_orig.connect
def _bft_aiosqlite_connect(*args, **kwargs):
    kwargs.setdefault('timeout', 5.0)
    class BFTConnectionContext:
        def __init__(self, *args, **kwargs):
            self._conn_future = _orig_aiosqlite_connect(*args, **kwargs)
        async def __aenter__(self):
            self.conn = await self._conn_future.__aenter__()
            await self.conn.execute("PRAGMA journal_mode=WAL;")
            await self.conn.execute("PRAGMA busy_timeout=5000;")
            await self.conn.execute("PRAGMA synchronous=NORMAL;")
            return self.conn
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            await self._conn_future.__aexit__(exc_type, exc_val, exc_tb)
        def __await__(self):
            async def _init():
                conn = await self._conn_future
                await conn.execute("PRAGMA journal_mode=WAL;")
                await conn.execute("PRAGMA busy_timeout=5000;")
                await conn.execute("PRAGMA synchronous=NORMAL;")
                return conn
            return _init().__await__()
    return BFTConnectionContext(*args, **kwargs)
_aiosqlite_bft_orig.connect = _bft_aiosqlite_connect
# ----------------------------------------
"""

def patch_file(filepath):
    try:
        with open(filepath, 'r') as f:
            content = f.read()
    except Exception as e:
        return False
        
    if "# --- C5-REAL BFT PATCH (R10) ---" in content or "# --- C5-REAL BFT PATCH AIOSQLITE (R10) ---" in content:
        return False # Already patched
        
    patched = False
    
    if "import sqlite3" in content or "from sqlite3" in content:
        content = content.replace("import sqlite3\n", "import sqlite3\n" + SQLITE_PATCH)
        patched = True
        
    if "import aiosqlite" in content:
        content = content.replace("import aiosqlite\n", "import aiosqlite\n" + AIOSQLITE_PATCH)
        patched = True
        
    if patched:
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"[+] Patched BFT R10 in: {filepath}")
        return True
    return False

def scan_and_patch(directory):
    count = 0
    for root, _, files in os.walk(directory):
        if '.venv' in root or '.git' in root or 'node_modules' in root:
            continue
        for file in files:
            if file.endswith('.py'):
                path = os.path.join(root, file)
                if patch_file(path):
                    count += 1
    print(f"[*] Total files patched in {directory}: {count}")

if __name__ == "__main__":
    targets = [
        "/Users/borjafernandezangulo/10_PROJECTS/cortex-persist",
        "/Users/borjafernandezangulo/10_PROJECTS/cortex-meta",
        "/Users/borjafernandezangulo/10_PROJECTS/cortex-head"
    ]
    for target in targets:
        if os.path.exists(target):
            scan_and_patch(target)
