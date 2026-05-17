import sqlite3
import os
import base64
from cortex.crypto.aes import CortexEncrypter
from cortex.crypto.keyring import get_master_key

DB_PATH = os.path.expanduser("~/.cortex/cortex.db")
TEST_KEY = base64.b64decode("MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA=")


def audit():
    if not os.path.exists(DB_PATH):
        print(f"DB not found at {DB_PATH}")
        return

    master_key = get_master_key()
    encrypter_prod = CortexEncrypter(master_key)
    encrypter_test = CortexEncrypter(TEST_KEY)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    names = ["Oliver", "Benji", "Tom"]
    found_facts = []
    cursor.execute("SELECT id, content, tenant_id FROM facts")
    rows = cursor.fetchall()

    import re

    for fid, content, tenant_id in rows:
        decrypted = None

        # Try Prod Key
        try:
            decrypted = encrypter_prod.decrypt_str(content, tenant_id=tenant_id)
        except Exception:
            # Try Test Key
            try:
                decrypted = encrypter_test.decrypt_str(content, tenant_id=tenant_id)
            except Exception:
                # Try Plain (if it's not encrypted)
                if not content.startswith("v6_aesgcm:"):
                    decrypted = content

        if decrypted:
            found_names = []
            for name in names:
                if re.search(rf"\b{name}\b", decrypted, re.IGNORECASE):
                    found_names.append(name)

            if found_names:
                found_facts.append((fid, decrypted, found_names))

    print(f"--- Audit Results for {', '.join(names)} ---")
    if not found_facts:
        print("No matches found in decrypted content.")
    else:
        for fid, content, matched_names in found_facts:
            print(f"[Fact {fid}] (Matched: {', '.join(matched_names)}): {content}")
            print("-" * 40)

    conn.close()


if __name__ == "__main__":
    audit()
