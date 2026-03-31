import sqlite3

import numpy as np
import sqlite_vec

db = sqlite3.connect(":memory:")
db.enable_load_extension(True)
sqlite_vec.load(db)

try:
    db.execute("CREATE VIRTUAL TABLE vec_int USING vec0(embedding int8[4])")
    print("SUCCESS CREATE int8")
except Exception as e:
    print("CREATE INT8 ERROR:", e)

try:
    db.execute("INSERT INTO vec_int(rowid, embedding) VALUES (?, ?)", (1, np.array([1,2,3,4], dtype=np.int8).tobytes()))
    print("SUCCESS INSERT raw int8")
except Exception as e:
    print("INSERT RAW INT8 ERROR:", e)

try:
    db.execute("INSERT INTO vec_int(rowid, embedding) VALUES (?, ?)", (2, b"\x01" + np.array([1,2,3,4], dtype=np.int8).tobytes()))
    print("SUCCESS INSERT int8 1 byte header")
except Exception as e:
    print("INSERT INT8 +1 ERROR:", e)

try:
    db.execute("INSERT INTO vec_int(rowid, embedding) VALUES (?, ?)", (3, b"\x01\x00" + np.array([1,2,3,4], dtype=np.int8).tobytes()))
    print("SUCCESS INSERT int8 2 byte header")
except Exception as e:
    print("INSERT INT8 +2 ERROR:", e)

try:
    # use vec_pack_int8 maybe?
    v = db.execute("SELECT vec_pack_int8(json_array(1,2,3,4))").fetchone()[0]
    db.execute("INSERT INTO vec_int(rowid, embedding) VALUES (?, ?)", (4, v))
    print("SUCCESS INSERT vec_pack_int8")
except Exception as e:
    print("INSERT vec_pack_int8 ERROR:", e)
