# [C5-REAL] Exergy-Maximized
import sqlite3
from pathlib import Path

db_path = "/private/var/folders/r_/hw1ds2nj49zffr6r4m_81r5h0000gn/T/pytest-of-borjafernandezangulo/pytest-237/test_execute_task0/cortex_execution_ledger.json"

if not Path(db_path).exists():
    print("DB does not exist.")
else:
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT * FROM cortex_execution_ledger")
    print(c.fetchall())
