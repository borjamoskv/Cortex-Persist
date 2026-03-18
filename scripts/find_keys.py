import base64

import keyring

from cortex.crypto.aes import CortexEncrypter

services = ["cortex_v6", "cortex_v5", "cortex", "cortex-persist"]
keys = ["master_key", "cortex_master_key", "encryption_key", "vault_key"]

target_fact = "v6_aesgcm:ZoLdo110Etpje/aGWd07wgIcHZoNSPiR9xI80gwa2SnHMIFN1AYnIe/dwD4mDyZ4DETsNsiCRuOe6ZiH5hbVOUJTKQH3XvRWF7A8syhfZVACu3r6rcz9X8cFcOe+E0j3gPpL/bM6uoFrRWIJKFSFHObZQ9wa"


def try_decrypt(key_b64):
    try:
        raw = base64.b64decode(key_b64)
        if len(raw) != 32:
            return False, "Wrong length"
        enc = CortexEncrypter(raw)
        dec = enc.decrypt_str(target_fact, tenant_id="default")
        return True, dec
    except Exception as e:
        return False, str(e)


print("Scavenging Keychain for valid keys...")
for s in services:
    for k in keys:
        try:
            val = keyring.get_password(s, k)
            if val:
                print(f"Found something in {s}/{k}")
                success, result = try_decrypt(val)
                if success:
                    print(f"!!! SUCCESS with {s}/{k} !!!")
                    print(f"Key: {val}")
                    print(f"Decrypted: {result}")
                else:
                    print(f"  Fail: {result}")
        except Exception:
            continue

print("Done.")
