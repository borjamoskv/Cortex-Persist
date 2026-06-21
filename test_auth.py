import sqlite3
def cb(*args): return sqlite3.SQLITE_DENY
db = sqlite3.connect(":memory:")
db.set_authorizer(cb)
try:
    db.execute("CREATE TABLE t (id int)")
except Exception as e:
    print(f"EXCEPTION: {type(e)}")
    print(f"MESSAGE: {e}")
