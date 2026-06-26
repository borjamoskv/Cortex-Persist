import sqlite3
import sqlite_vec

conn = sqlite3.connect(':memory:')
conn.enable_load_extension(True)
sqlite_vec.load(conn)
try:
    conn.executescript("""
        CREATE VIRTUAL TABLE IF NOT EXISTS vec_facts USING vec0(
            embedding int8[384]
        );
        CREATE TABLE IF NOT EXISTS vec_void (
            rowid INTEGER PRIMARY KEY,
            embedding BLOB
        );
        CREATE TABLE IF NOT EXISTS vec_void_mih (
            rowid INTEGER PRIMARY KEY,
            s0 INTEGER, s1 INTEGER, s2 INTEGER, s3 INTEGER,
            s4 INTEGER, s5 INTEGER, s6 INTEGER, s7 INTEGER,
            s8 INTEGER, s9 INTEGER, s10 INTEGER, s11 INTEGER,
            s12 INTEGER, s13 INTEGER, s14 INTEGER, s15 INTEGER
        );
    """)
    print("Success executescript full")
except Exception as e:
    print(f"Error: {e}")
