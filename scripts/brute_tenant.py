import base64

from cortex.crypto.aes import CortexEncrypter

# The only key we found
key_b64 = "Bh85q95WzJv4SKuPH3GWCFTyjIwf4n/x7uso+1Cor08="
target_fact = "v6_aesgcm:ZoLdo110Etpje/aGWd07wgIcHZoNSPiR9xI80gwa2SnHMIFN1AYnIe/dwD4mDyZ4DETsNsiCRuOe6ZiH5hbVOUJTKQH3XvRWF7A8syhfZVACu3r6rcz9X8cFcOe+E0j3gPpL/bM6uoFrRWIJKFSFHObZQ9wa"

tenants = [
    "default",
    "admin",
    "system",
    "cortex",
    "user",
    "borja",
    "borjafernandezangulo",
    "borjamoskv",
    "swarm",
    "legion",
]


def try_decrypt(key_b64, tenant):
    try:
        raw = base64.b64decode(key_b64)
        enc = CortexEncrypter(raw)
        dec = enc.decrypt_str(target_fact, tenant_id=tenant)
        return True, dec
    except Exception as e:
        return False, str(e)


print(f"Brute-forcing tenant IDs for key: {key_b64}...")
for t in tenants:
    success, result = try_decrypt(key_b64, t)
    if success:
        print(f"!!! SUCCESS with tenant: {t} !!!")
        print(f"Decrypted: {result}")
        break
    else:
        # print(f"  Fail {t}: {result}")
        pass
else:
    print("No tenant ID worked.")
