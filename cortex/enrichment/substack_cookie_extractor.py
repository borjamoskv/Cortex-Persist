import os
import sqlite3
import subprocess

import keyring
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


def get_chrome_key():
    # Attempt to retrieve via security CLI (forces system dialog if not authorized)
    try:
        cmd = ['security', 'find-generic-password', '-w', '-s', 'Chrome Safe Storage', '-a', 'Chrome']
        password = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).strip()
        return password
    except Exception:
        # Fallback to keyring library
        try:
            return keyring.get_password("Chrome Safe Storage", "Chrome").encode('utf-8')
        except Exception as e:
            print(f"Failed to retrieve Chrome key from Keychain: {e}")
            return None

def decrypt_cookie(encrypted_value, key):
    if not encrypted_value or not key:
        return ""
    # Chrome on macOS uses AES-CBC with a key derived via PBKDF2
    # Salt is b'saltysalt', iterations = 10003, IV = 16 spaces
    salt = b'saltysalt'
    iv = b' ' * 16
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA1(),
        length=16,
        salt=salt,
        iterations=10003
    )
    derived_key = kdf.derive(key)
    
    cipher = Cipher(algorithms.AES(derived_key), modes.CBC(iv))
    decryptor = cipher.decryptor()
    
    # Strip the v10 prefix if present
    if encrypted_value.startswith(b'v10'):
        encrypted_value = encrypted_value[3:]
        
    decrypted = decryptor.update(encrypted_value) + decryptor.finalize()
    
    # Unpad (PKCS#7)
    padding_len = decrypted[-1]
    if padding_len < 16:
        decrypted = decrypted[:-padding_len]
        
    return decrypted.decode('utf-8', errors='ignore')

def get_substack_cookies(db_path, key):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT host_key, name, encrypted_value FROM cookies WHERE host_key LIKE '%substack%'")
    
    cookies = {}
    for host, name, enc_val in cursor.fetchall():
        try:
            decrypted = decrypt_cookie(enc_val, key)
            if decrypted:
                cookies[name] = decrypted
        except Exception as e:
            print(f"Error decrypting {name} for {host}: {e}")
            
    conn.close()
    return cookies

if __name__ == "__main__":
    key = get_chrome_key()
    if key:
        print(f"Successfully retrieved key from Keychain. Length: {len(key)}")
        profiles = ["Default", "Profile 1", "Profile 2", "Profile 3", "Default/Default"]
        for prof in profiles:
            db_path = os.path.expanduser(f"~/Library/Application Support/Google/Chrome/{prof}/Cookies")
            if os.path.exists(db_path):
                print(f"Checking profile: {prof} at {db_path}")
                cookies = get_substack_cookies(db_path, key)
                if cookies:
                    print(f"Found {len(cookies)} Substack cookies in {prof}:")
                    for k in cookies:
                        # Print securely
                        print(f"  Cookie: {k} = {cookies[k][:5]}...[len={len(cookies[k])}]")
    else:
        print("Could not retrieve key.")
