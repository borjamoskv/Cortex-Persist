import sqlite3
import sys
import os

sys.path.append("/Users/borjafernandezangulo/cortex")
from cortex.search import text_search

try:
    conn = sqlite3.connect(":memory:")
    conn.close()
    print("calling text_search...")
    res = text_search(conn, "foo")
    print(f"Result: {res}")
except Exception as e:
    print(f"Caught top level: {type(e).__name__}: {e}")
