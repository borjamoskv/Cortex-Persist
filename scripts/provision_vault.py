import os
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

def provision_vault():
    print("--- CORTEX VAULT PROVISIONING ---")
    
    # 1. Generate Key
    key = AESGCM.generate_key(bit_length=256)
    encoded_key = base64.b64encode(key).decode("utf-8")
    
    # 2. Instructions for the user
    print("\n[!] IMPORTANT: Sovereign Key Generated.")
    print(f"CORTEX_VAULT_KEY={encoded_key}")
    print("\nAction Required:")
    print("1. Export this key to your environment: export CORTEX_VAULT_KEY='...'")
    print("2. Or add it to your .env file.")
    
    # 3. Create secure storage directory if it doesn't exist
    vault_dir = os.path.expanduser("~/.cortex/vault")
    os.makedirs(vault_dir, exist_ok=True)
    print(f"\n[+] Secure storage initialized at: {vault_dir}")
    
    return encoded_key

if __name__ == "__main__":
    provision_vault()
