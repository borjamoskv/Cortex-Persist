import base64
import sys

from cortex.crypto import get_default_encrypter, get_master_key


def test_decrypt(encrypted_str):
    key = get_master_key()
    print(f"Master Key available: {key is not None}")
    if key:
        print(f"Master Key (b64): {base64.b64encode(key).decode()}")

    enc = get_default_encrypter()
    print(f"Encrypter active: {enc.is_active}")

    try:
        decrypted = enc.decrypt_str(encrypted_str, tenant_id="default")
        print(f"Decrypted: {decrypted}")
    except Exception as e:
        print(f"Decryption failed: {e}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_decrypt(sys.argv[1])
    else:
        print("Usage: python scripts/diag_crypto.py <encrypted_str>")
