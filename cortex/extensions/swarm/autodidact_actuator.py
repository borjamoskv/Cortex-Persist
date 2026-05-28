import logging

from cortex.extensions.swarm.sortu_jit_executor import run_jit_sandbox

logger = logging.getLogger("cortex.autodidact.actuator")
logging.basicConfig(level=logging.INFO)


async def autodidact_ingest(source_code: str, expected_yield_gain: float, metadata: dict) -> dict:
    """
    Sovereign Autodidact-Omega Actuator Pipeline (v4.0)
    1. Parse and JIT execute
    2. Thermometer (Yield Calculation)
    3. Return structured payload for Ledger (if valid)
    """
    logger.info("🔥 [AUTODIDACT-Ω] Starting Thermodynamic Ingestion...")

    # 1. AST Sandbox Execution
    try:
        sandbox_res = await run_jit_sandbox(source_code, timeout_ms=500)
    except Exception as e:
        # Purge -> Stigmergic / Cicatricial Tissue handling is 'silent purge' per rules
        logger.warning("🔥 [AUTODIDACT-Ω] PURGED. AST Execution Failed: %s", e)
        return {"action": "PURGE", "reason": "JIT_BREAKER", "details": str(e)}

    if sandbox_res["status"] == "failed":
        logger.warning("🔥 [AUTODIDACT-Ω] PURGED. Epistemic Failure: %s", sandbox_res["error"])
        return {"action": "PURGE", "reason": "LOGIC_ERROR", "details": sandbox_res["error"]}

    # 2. Yield & Thermometer estimation
    exec_time = sandbox_res["time_ms"]

    # Mathematical integration: we estimate the 'Thermodynamic Resonance' based on speed.
    # We require <500ms natively via the bounds, but an execution >300ms is considered "noisy".
    # multiprocessing spawn overhead in macOS takes ~30-100ms on its own.
    performance_resonance = 1.0 if exec_time < 150 else (0.5 if exec_time < 300 else 0.1)

    # Enforcing Axiom Ω2: If the operation doesn't resonate positively against the exergy expenditure, we abort.
    if performance_resonance < 0.2:
        logger.warning(
            "🔥 [AUTODIDACT-Ω] PURGED. Negative Thermodynamic Yield (%.2fms).", exec_time
        )
        return {"action": "PURGE", "reason": "NEGATIVE_YIELD", "yield": exec_time}

    # 3. Sovereign Validation pass
    logger.info(
        "🔥 [AUTODIDACT-Ω] SUCCESS. O(1) Yield Crystal Forged (Resonance: %s).",
        performance_resonance,
    )
    return {
        "action": "CRYSTALLIZE",
        "yield_time_ms": exec_time,
        "resonance": performance_resonance,
        "locals": str(list(sandbox_res["result"].keys())),
    }
