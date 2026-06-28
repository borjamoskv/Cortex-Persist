import sys
from cortex.crypto.aes import get_default_encrypter
enc = get_default_encrypter()
val = "v6_aesgcm:kcGOKaGne+fmXkV46jsJZqxoxkI2bBPLWGLHjoxZCa3E/NQKY61eAU5DZg=="
print(enc.decrypt_str(val))
