
with open("cortex/auth/manager.py") as f:
    code = f.read()

# 1. Fix __init__ dummy_hash exception handling
init_target = """        try:
            self._dummy_hash = getattr(cortex_rs, "hash_password")("ctx_dummy_key_to_initialize_hashing_parameters")  # noqa: B009
        except Exception:
            self._dummy_hash = "$argon2id$v=19$m=16,t=2,p=1$stub$dummyhash\""""
init_replace = """        try:
            self._dummy_hash = getattr(cortex_rs, "hash_password")("ctx_dummy_key_to_initialize_hashing_parameters")  # noqa: B009
        except AttributeError:
            raise RuntimeError("FATAL: cortex_rs FFI broken. Zero-Trust cannot downgrade.")"""
code = code.replace(init_target, init_replace)

# 2. Fix hash_key_argon2id_async
hash_target = """        try:
            hash_fn = getattr(cortex_rs, "hash_password")  # noqa: B009
            return await loop.run_in_executor(
                self._executor, hash_fn, key + AUTH_PEPPER
            )
        except AttributeError:
            logger.warning("cortex_rs.hash_password missing. Falling back to stub.")
            return (
                f"$argon2id$v=19$m=16,t=2,p=1$stub${self.hash_key_legacy_sha256(key + AUTH_PEPPER)}"
            )"""
hash_replace = """        hash_fn = getattr(cortex_rs, "hash_password")  # noqa: B009
        if hash_fn is None:
            raise RuntimeError("FATAL: cortex_rs FFI broken.")
        return await loop.run_in_executor(
            self._executor, hash_fn, key + AUTH_PEPPER
        )"""
code = code.replace(hash_target, hash_replace)

# 3. Fix verify_password logic
verify_target = """            try:
                loop = asyncio.get_running_loop()
                try:
                    verify_fn = getattr(cortex_rs, "verify_password")  # noqa: B009
                    if verify_fn is None:
                        raise TypeError("verify_password not found")
                    is_valid = await loop.run_in_executor(
                        self._executor,
                        verify_fn,
                        raw_key + AUTH_PEPPER,
                        target_hash,
                    )
                except TypeError:
                    # if getattr returned None
                    stub_hash = f"$argon2id$v=19$m=16,t=2,p=1$stub${self.hash_key_legacy_sha256(raw_key + AUTH_PEPPER)}"
                    is_valid = stub_hash == target_hash
            except Exception as e:
                logger.exception("Cryptographic backend failure during token verification: %s", e)"""
verify_replace = """            try:
                loop = asyncio.get_running_loop()
                verify_fn = getattr(cortex_rs, "verify_password")  # noqa: B009
                if verify_fn is None:
                    raise RuntimeError("FATAL: cortex_rs FFI broken. Zero-Trust cannot downgrade.")
                is_valid = await loop.run_in_executor(
                    self._executor,
                    verify_fn,
                    raw_key + AUTH_PEPPER,
                    target_hash,
                )
            except Exception as e:
                logger.exception("Cryptographic backend failure during token verification: %s", e)
                is_valid = False"""
code = code.replace(verify_target, verify_replace)

with open("cortex/auth/manager.py", "w") as f:
    f.write(code)
print("Auth manager patched successfully.")
