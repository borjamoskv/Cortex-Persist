import os
import ctypes
import sys

def wipe_c_env(key: str):
    # Load the C standard library
    libc = ctypes.CDLL(None)
    
    # Try to find 'environ' symbol. On macOS it might be '_environ'.
    try:
        if sys.platform == 'darwin':
            # On macOS, environ is accessed via _NSGetEnviron
            ns_get_environ = libc._NSGetEnviron
            ns_get_environ.restype = ctypes.POINTER(ctypes.POINTER(ctypes.c_char_p))
            environ = ns_get_environ().contents
        else:
            environ = ctypes.POINTER(ctypes.c_char_p).in_dll(libc, 'environ')
    except Exception as e:
        print(f"Error getting environ: {e}")
        return

    # Iterate through environ strings
    i = 0
    key_bytes = key.encode('utf-8') + b'='
    while environ[i]:
        env_str = ctypes.string_at(environ[i])
        if env_str.startswith(key_bytes):
            print(f"Found {key} in C environ at offset {i}")
            # Wipe it!
            length = len(env_str)
            ctypes.memset(environ[i], 0, length)
            print("Wiped.")
            break
        i += 1

if __name__ == '__main__':
    key = "ULTRA_SECRET_P100"
    os.environ[key] = "THE_ACTUAL_SECRET_VALUE_12345"
    
    print(f"Before C-wipe, Python os.environ: {os.environ.get(key)}")
    wipe_c_env(key)
    
    # After C wipe, does Python still see it if we bypass cache?
    # os.environ might cache it, but let's check os.getenv which bypasses Python's os.environ cache
    # actually os.getenv just uses os.environ.
    # To check C level, we can use libc.getenv
    libc = ctypes.CDLL(None)
    libc.getenv.restype = ctypes.c_char_p
    c_val = libc.getenv(key.encode('utf-8'))
    print(f"After C-wipe, C getenv: {c_val}")
    print(f"After C-wipe, Python os.environ: {os.environ.get(key)}")
