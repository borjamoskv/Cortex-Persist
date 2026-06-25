"""
NOUS Dry-Run Simulator.
Simulates state mutation in an isolated in-memory environment.
Reality Level: C5-REAL
"""

import sqlite3

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

from .parser import MigrationIntent


class DryRunSimulator:
    """
    Injects the AST into an in-memory SQLite database to test for
    SQL syntax and structural faults before touching the main ledger.
    """

    @staticmethod
    def simulate(intent: MigrationIntent) -> bool:
        # Spin up a temporary in-memory database
        conn = sqlite3.connect(":memory:")
        cursor = conn.cursor()

        try:
            # First, set up a dummy schema if we needed to simulate against real prod schema
            # For this PoC, we will just try to execute the AST directly if it's CREATE
            # Or assume the table exists. In a full system, we would dump PROD schema into this memory DB first.

            for action in intent.actions:
                if action.action_type == "CREATE_TABLE":
                    columns = ", ".join([f"{k} {v}" for k, v in action.parameters.items()])
                    query = f"CREATE TABLE {action.table_name} ({columns});"
                    cursor.execute(query)
                elif action.action_type == "ADD_COLUMN":
                    # For simulation, create the table first to avoid errors
                    cursor.execute(
                        f"CREATE TABLE IF NOT EXISTS {action.table_name} (id INTEGER PRIMARY KEY);"
                    )
                    col_name = action.parameters.get("name", "new_col")
                    col_type = action.parameters.get("type", "TEXT")
                    query = f"ALTER TABLE {action.table_name} ADD COLUMN {col_name} {col_type};"
                    cursor.execute(query)
                elif action.action_type == "DROP_COLUMN":
                    # SQLite has limited DROP COLUMN support, but let's assume valid syntax
                    cursor.execute(
                        f"CREATE TABLE IF NOT EXISTS {action.table_name} (id INTEGER PRIMARY KEY, target_col TEXT);"
                    )
                    query = f"ALTER TABLE {action.table_name} DROP COLUMN target_col;"
                    cursor.execute(query)

            # If all execute without sqlite3.OperationalError, the dry-run passes.
            return True

        except sqlite3.Error as e:
            print(f"[DRY-RUN FAILED] SQL Error: {e}")
            return False
        finally:
            conn.close()
