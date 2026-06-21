import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'causal_demo.db')

def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            type TEXT,
            actor TEXT,
            payload TEXT,
            parent_event INTEGER,
            prev_hash TEXT,
            event_hash TEXT
        )
    """)
    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
