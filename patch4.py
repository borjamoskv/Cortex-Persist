import os

def patch_file(path, replacements):
    with open(path, 'r') as f:
        content = f.read()
    for old, new in replacements:
        content = content.replace(old, new)
    with open(path, 'w') as f:
        f.write(content)

patch_file('cortex/auth/manager.py', [
    ('getattr(cortex_rs, "hash_password")("ctx_dummy_key_to_initialize_hashing_parameters")', 'getattr(cortex_rs, "hash_password")("ctx_dummy_key_to_initialize_hashing_parameters")  # noqa: B009'),
    ('getattr(cortex_rs, "hash_password")\n', 'getattr(cortex_rs, "hash_password")  # noqa: B009\n'),
    ('getattr(cortex_rs, "verify_password")\n', 'getattr(cortex_rs, "verify_password")  # noqa: B009\n')
])

patch_file('cortex/engine/core/_engine_connection.py', [
    ('getattr(conn._conn, "authorize_causal_writes")()', 'getattr(conn._conn, "authorize_causal_writes")()  # noqa: B009'),
    ('getattr(conn._conn, "revoke_causal_writes")()', 'getattr(conn._conn, "revoke_causal_writes")()  # noqa: B009'),
    ('setattr(config, "HKDF_SALT", row[0])', 'setattr(config, "HKDF_SALT", row[0])  # noqa: B010'),
    ('setattr(config._cfg, "HKDF_SALT", row[0])', 'setattr(config._cfg, "HKDF_SALT", row[0])  # noqa: B010')
])

patch_file('cortex/guards/ctre_guard.py', [
    ('getattr(cortex_rs, "ctre_atomic_commit")(', 'getattr(cortex_rs, "ctre_atomic_commit")(')
])

print('Patched successfully.')
