import sqlite3
import os
import base64
from cortex.crypto.aes import CortexEncrypter
from cortex.crypto.keyring import get_master_key

DB_PATH = os.path.expanduser("~/.cortex/cortex.db")
TEST_KEY = base64.b64decode("MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA=")


def dump_all():
    if not os.path.exists(DB_PATH):
        print(f"DB not found at {DB_PATH}")
        return

    master_key = get_master_key()
    encrypter_prod = CortexEncrypter(master_key)
    encrypter_test = CortexEncrypter(TEST_KEY)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, content, tenant_id FROM facts")
    rows = cursor.fetchall()

    for fid, content, tenant_id in rows:
        decrypted = None
        method = "UNKNOWN"

        # Try Prod Key
        try:
            decrypted = encrypter_prod.decrypt_str(content, tenant_id=tenant_id)
            method = "PROD"
        except Exception:
            # Try Test Key
            try:
                decrypted = encrypter_test.decrypt_str(content, tenant_id=tenant_id)
                method = "TEST"
            except Exception:
                # Try Plain
                if not content.startswith("v6_aesgcm:"):
                    decrypted = content
                    method = "PLAIN"

        if decrypted:
            print(f"--- Fact {fid} ({method}) ---")
            print(decrypted)
            print("-" * 40)
        else:
            print(f"--- Fact {fid} (FAILED DECRYPTION) ---")

    conn.close()


if __name__ == "__main__":
    dump_all()
