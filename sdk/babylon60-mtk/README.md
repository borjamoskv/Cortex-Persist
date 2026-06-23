# babylon60-mtk

**Minimal Trusted Kernel (MTK) - SQLite Cryptographic Authorizer Hook**

A lightweight, physical runtime coercion library that prevents state mutation in SQLite databases unless explicitly authorized by an ephemeral cryptographic token. 

Designed to stop stochastic AI agents (LLMs) from destroying or corrupting database memory by intercepting the C/Rust execution layer of SQLite.

## Installation

```bash
pip install babylon60-mtk
```

## Usage

```python
import sqlite3
from babylon60_mtk import install_mtk_authorizer, mtk_active_token

conn = sqlite3.connect(":memory:")

# Install the physical hook
install_mtk_authorizer(conn)

# All READ operations work normally
conn.execute("SELECT sqlite_version();")

# All WRITE operations will now be blocked with SQLITE_DENY
try:
    conn.execute("INSERT INTO my_table (data) VALUES ('unauthorized')")
except sqlite3.DatabaseError:
    print("Blocked by MTK!")

# Writes are only permitted when a valid ephemeral token is active in the ContextVar
token_id = mtk_active_token.set("mtk_auth_1234_valid")
try:
    conn.execute("INSERT INTO my_table (data) VALUES ('authorized')")
finally:
    mtk_active_token.reset(token_id)
```

## Authors
Borja Moskv (borjamoskv) - BABYLON-60 C5-REAL Architecture
