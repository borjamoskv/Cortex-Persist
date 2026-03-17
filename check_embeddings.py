import sqlite3
import sqlite_vec
from pathlib import Path

db_path = Path('~/.cortex/cortex.db').expanduser()
conn = sqlite3.connect(str(db_path))
conn.enable_load_extension(True)
sqlite_vec.load(conn)
conn.enable_load_extension(False)

try:
    res = conn.execute("SELECT count(*) FROM fact_embeddings").fetchone()[0]
    print(f"Embeddings: {res}")
    
    # Check a few IDs
    res = conn.execute("SELECT fact_id FROM fact_embeddings LIMIT 5").fetchall()
    print(f"Sample Embedding IDs: {[r[0] for r in res]}")
    
    # Check facts IDs
    res = conn.execute("SELECT id FROM facts LIMIT 5").fetchall()
    print(f"Sample Fact IDs: {[r[0] for r in res]}")
except Exception as e:
    print(f"Error: {e}")
finally:
    conn.close()
