import os
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
import time
from typing import Any

# C5-REAL: Metrics Database for Benchmark Suite

DB_PATH = os.path.expanduser("~/.gemini/config/.cortex/benchmark_metrics.db")

class MetricsDB:
    def __init__(self):
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        self.conn = sqlite3.connect(DB_PATH)
        self._init_schema()

    def _init_schema(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Runs (
                run_id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                task_id TEXT NOT NULL,
                timestamp REAL NOT NULL,
                time_to_first_change REAL,
                total_latency REAL,
                successful_completion INTEGER,
                tokens_used INTEGER,
                api_cost REAL,
                tests_passed INTEGER,
                rollback_events INTEGER,
                invalid_mutations INTEGER,
                commits_created INTEGER,
                hash_chain_validity INTEGER,
                exergy_efficiency REAL
            )
        ''')
        self.conn.commit()

    def record_run(self, run_data: dict[str, Any]):
        """Registra una ejecución completa del benchmark."""
        # Calculamos eficiencia de exergía: (verified_actions / tokens_used) * 1000
        # verified_actions = tests_passed + commits_created
        actions = run_data.get('tests_passed', 0) + run_data.get('commits_created', 0)
        tokens = run_data.get('tokens_used', 1) # prevent div by zero
        if tokens == 0:
            tokens = 1
        
        exergy_efficiency = (actions / tokens) * 1000
        run_data['exergy_efficiency'] = exergy_efficiency
        
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO Runs (
                run_id, agent_id, task_id, timestamp, time_to_first_change, 
                total_latency, successful_completion, tokens_used, api_cost, 
                tests_passed, rollback_events, invalid_mutations, 
                commits_created, hash_chain_validity, exergy_efficiency
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            run_data['run_id'], run_data['agent_id'], run_data['task_id'], time.time(),
            run_data.get('time_to_first_change'), run_data.get('total_latency'),
            run_data.get('successful_completion', 0), run_data.get('tokens_used', 0),
            run_data.get('api_cost', 0.0), run_data.get('tests_passed', 0),
            run_data.get('rollback_events', 0), run_data.get('invalid_mutations', 0),
            run_data.get('commits_created', 0), run_data.get('hash_chain_validity', 1),
            exergy_efficiency
        ))
        self.conn.commit()
        return exergy_efficiency

    def get_agent_comparison(self) -> str:
        """Devuelve un string tabular comparando la Exergy_Efficiency media por agente."""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT agent_id, AVG(exergy_efficiency), AVG(total_latency), SUM(successful_completion)
            FROM Runs
            GROUP BY agent_id
        ''')
        results = cursor.fetchall()
        
        output = "BENCHMARK AGENT COMPARISON:\\n"
        output += f"{'Agent ID':<15} | {'Avg Exergy (x1000)':<20} | {'Avg Latency (s)':<18} | {'Successes':<10}\\n"
        output += "-" * 70 + "\\n"
        for row in results:
            output += f"{row[0]:<15} | {row[1]:<20.2f} | {row[2]:<18.2f} | {row[3]:<10}\\n"
        return output
