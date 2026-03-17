import sqlite3

from cortex.crypto.aes import get_default_encrypter

enc = get_default_encrypter()
conn = sqlite3.connect("/Users/borjafernandezangulo/.cortex/cortex.db")
c = conn.cursor()
c.execute("SELECT id, project, fact_type, meta FROM facts WHERE meta LIKE 'v6_aesgcm:%'")
rows = c.fetchall()
for r in rows:
    try:
        enc.decrypt_str(r[3])
    except Exception as e:
        print(f"FAILED on ID={r[0]}, type={r[2]}, project={r[1]}, error={e}")
