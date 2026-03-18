import base64

from cortex.crypto import get_default_encrypter, get_master_key


def test_crypto():
    key = get_master_key()
    print(f"Master Key available: {key is not None}")
    if key:
        print(f"Master Key length: {len(key)}")
        print(f"Master Key (b64): {base64.b64encode(key).decode()}")

    enc = get_default_encrypter()
    print(f"Encrypter active: {enc.is_active}")

    test_str = "hello world"
    encrypted = enc.encrypt_str(test_str, tenant_id="default")
    print(f"Encrypted: {encrypted}")

    try:
        decrypted = enc.decrypt_str(encrypted, tenant_id="default")
        print(f"Decrypted: {decrypted}")
        assert test_str == decrypted
        print("Self-test passed!")
    except Exception as e:
        print(f"Self-test failed: {e}")


if __name__ == "__main__":
    test_crypto()
