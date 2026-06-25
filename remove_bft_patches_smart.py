import os
import sys

patch_lines_set = {
    "# --- C5-REAL BFT PATCH (R10) ---",
    "# --- C5-REAL BFT PATCH AIOSQLITE (R10) ---",
    "import sqlite3 as _sqlite3_bft_orig",
    "import aiosqlite as _aiosqlite_bft_orig",
    "_orig_sqlite_connect = _sqlite3_bft_orig.connect",
    "_orig_aiosqlite_connect = _aiosqlite_bft_orig.connect",
    "def _bft_sqlite_connect(*args, **kwargs):",
    "def _bft_aiosqlite_connect(*args, **kwargs):",
    "kwargs.setdefault('timeout', 5.0)",
    "conn = _orig_sqlite_connect(*args, **kwargs)",
    "try:",
    "conn.execute(\"PRAGMA journal_mode=WAL;\")",
    "conn.execute(\"PRAGMA busy_timeout=5000;\")",
    "conn.execute(\"PRAGMA synchronous=NORMAL;\")",
    "except Exception:",
    "pass",
    "return conn",
    "_sqlite3_bft_orig.connect = _bft_sqlite_connect",
    "_aiosqlite_bft_orig.connect = _bft_aiosqlite_connect",
    "# -------------------------------",
    "# ----------------------------------------",
    "class BFTConnectionContext:",
    "def __init__(self, *args, **kwargs):",
    "self._conn_future = _orig_aiosqlite_connect(*args, **kwargs)",
    "async def __aenter__(self):",
    "self.conn = await self._conn_future.__aenter__()",
    "await self.conn.execute(\"PRAGMA journal_mode=WAL;\")",
    "await self.conn.execute(\"PRAGMA busy_timeout=5000;\")",
    "await self.conn.execute(\"PRAGMA synchronous=NORMAL;\")",
    "return self.conn",
    "async def __aexit__(self, exc_type, exc_val, exc_tb):",
    "await self._conn_future.__aexit__(exc_type, exc_val, exc_tb)",
    "def __await__(self):",
    "async def _init():",
    "conn = await self._conn_future",
    "await conn.execute(\"PRAGMA journal_mode=WAL;\")",
    "await conn.execute(\"PRAGMA busy_timeout=5000;\")",
    "await conn.execute(\"PRAGMA synchronous=NORMAL;\")",
    "return conn",
    "return _init().__await__()",
    "return BFTConnectionContext(*args, **kwargs)"
}
def clean_bft_patches(filepath):
    with open(filepath, 'r') as f:
        lines = f.readlines()
    new_lines = []
    modified = False
    in_patch = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        # Determine if we are entering or leaving a patch context
        if "C5-REAL BFT PATCH" in stripped:
            in_patch = True
        # If we are in a patch context, check if the line belongs to the patch
        is_patch_line = False
        if in_patch:
            # We treat empty lines inside a patch context as part of the patch
            if not stripped:
                is_patch_line = True
            elif stripped in patch_lines_set:
                is_patch_line = True
            # If we hit an import that is NOT in the patch set, we don't delete it!
            # e.g. `from cortex.engine.query_mixin import QueryMixin`
            # Check if this line is the end of the patch logic
            if stripped == "_sqlite3_bft_orig.connect = _bft_sqlite_connect" or \
               stripped == "_aiosqlite_bft_orig.connect = _bft_aiosqlite_connect" or \
               stripped.startswith("# ------"):
                # The patch ends here or very soon. 
                # We will mark it as a patch line, and exit patch context
                is_patch_line = True
                if stripped.startswith("# ------"):
                    in_patch = False
                # If it didn't have the closing dashes, we just exit on the assignment
                elif i + 1 < len(lines) and not lines[i+1].strip().startswith("# ------"):
                    in_patch = False
        if is_patch_line:
            modified = True
            continue
        new_lines.append(line)
    if modified:
        with open(filepath, 'w') as f:
            f.writelines(new_lines)
        return True
    return False
changed = 0
for root, dirs, files in os.walk('/Users/borjafernandezangulo/10_PROJECTS/cortex-persist'):
    if '.venv' in root or '.git' in root or 'legacy_research' in root:
        continue
    for file in files:
        if file.endswith('.py'):
            if clean_bft_patches(os.path.join(root, file)):
                changed += 1
print(f"Cleaned {changed} files.")
