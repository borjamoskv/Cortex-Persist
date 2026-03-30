import sqlite3
import sqlite_vec
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")
emb = model.encode(["hello world"])
print(emb.shape)

conn = sqlite3.connect(":memory:")
conn.enable_load_extension(True)
sqlite_vec.load(conn)
conn.enable_load_extension(False)

conn.execute("""
CREATE VIRTUAL TABLE vec_items USING vec0(
    embedding float[384]
);
""")

conn.execute("INSERT INTO vec_items(rowid, embedding) VALUES (?, ?)", (1, emb[0].tobytes()))
row = conn.execute("""
    SELECT rowid, distance
    FROM vec_items
    WHERE embedding MATCH ?
    ORDER BY distance
    LIMIT 1
""", (emb[0].tobytes(),)).fetchone()

print("Result:", row)
