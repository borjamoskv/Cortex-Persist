# Thin shim to expose Rust extension symbols

try:
    from cortex_rs import ZeroCopyRingBuffer, CortexRsSubstrate

    HAS_CORTEX_RS = True
except Exception as e:
    import warnings

    warnings.warn(f"CORTEX‑RS load failed: {e}", stacklevel=2)
    HAS_CORTEX_RS = False
