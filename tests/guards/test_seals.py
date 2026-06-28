# [C5-REAL] Exergy-Maximized
# This file is part of CORTEX. Apache-2.0.
import pytest
import json
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock
from cortex.guards.seals import (
    check_seal_1_code_quality,
    check_seal_2_type_safety,
    check_seal_3_security,
    check_seal_4_tests,
    check_seal_5_ledger,
    check_seal_6_async_perf,
    check_seal_7_axiom_registry,
    check_seal_8_dependency,
    check_seal_9_compliance,
    check_seal_10_preservation,
    GlobalSourceCache,
)


@pytest.fixture
def mock_cache():
    GlobalSourceCache.files = {}
    GlobalSourceCache._loaded = True
    yield GlobalSourceCache
    GlobalSourceCache.files = {}
    GlobalSourceCache._loaded = False


# --- SEAL 1: CODE QUALITY ---


@pytest.mark.asyncio
async def test_seal_1_happy(mock_cache):
    mock_cache.files = {Path("ok.py"): "code"}
    with patch("cortex.guards._seals_checks_1_5.arun_cmd", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = (0, "No issues")
        passed, _ = await check_seal_1_code_quality()
        assert passed is True


@pytest.mark.asyncio
async def test_seal_1_ruff_failure(mock_cache):
    mock_cache.files = {Path("ok.py"): "code"}
    with patch("cortex.guards._seals_checks_1_5.arun_cmd", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = (1, "Ruff error")
        passed, _ = await check_seal_1_code_quality()
        assert passed is False


@pytest.mark.asyncio
async def test_seal_1_loc_boundary(mock_cache):
    # Boundary: Exactly 700 lines
    mock_cache.files = {Path("boundary.py"): "\n" * 699}
    with patch("cortex.guards._seals_checks_1_5.arun_cmd", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = (0, "No issues")
        passed, _ = await check_seal_1_code_quality()
        assert passed is True


@pytest.mark.asyncio
async def test_seal_1_loc_rejection(mock_cache):
    # Rejection: 701 lines
    mock_cache.files = {Path("too_long.py"): "\n" * 700}
    with patch("cortex.guards._seals_checks_1_5.arun_cmd", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = (0, "No issues")
        passed, _ = await check_seal_1_code_quality()
        assert passed is False


# --- SEAL 2: TYPE SAFETY ---


@pytest.mark.asyncio
async def test_seal_2_happy():
    with patch("cortex.guards._seals_checks_1_5.arun_cmd", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = (0, "Success")
        passed, _ = await check_seal_2_type_safety()
        assert passed is True


@pytest.mark.asyncio
async def test_seal_2_rejection():
    with patch("cortex.guards._seals_checks_1_5.arun_cmd", new_callable=AsyncMock) as mock_run:
        # High error count
        mock_run.return_value = (1, '{"summary": {"errorCount": 200}}')
        passed, _ = await check_seal_2_type_safety()
        assert passed is False


@pytest.mark.asyncio
async def test_seal_2_boundary():
    with patch("cortex.guards._seals_checks_1_5.arun_cmd", new_callable=AsyncMock) as mock_run:
        # Exactly 78 errors (threshold)
        mock_run.return_value = (1, '{"summary": {"errorCount": 78}}')
        passed, _ = await check_seal_2_type_safety()
        assert passed is True


# --- SEAL 3: SECURITY ---


@pytest.mark.asyncio
async def test_seal_3_happy(mock_cache):
    with (
        patch("cortex.guards._seals_checks_1_5.arun_cmd", new_callable=AsyncMock) as mock_run,
        patch("cortex.swarm.legion_vectors.EntropyDemon") as mock_demon,
        patch("cortex.swarm.legion_vectors.Intruder") as mock_intruder,
    ):
        mock_run.return_value = (0, "No issues")
        mock_demon.return_value.attack = AsyncMock(return_value=[])
        mock_intruder.return_value.attack = AsyncMock(return_value=[])
        passed, _ = await check_seal_3_security()
        assert passed is True


@pytest.mark.asyncio
async def test_seal_3_bandit_rejection(mock_cache):
    with patch("cortex.guards._seals_checks_1_5.arun_cmd", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = (1, "Bandit found vulnerabilities")
        passed, _ = await check_seal_3_security()
        assert passed is False


@pytest.mark.asyncio
async def test_seal_3_demon_rejection(mock_cache):
    mock_cache.files = {Path("cortex/engine/bad.py"): "try: pass\nexcept: pass"}
    with (
        patch("cortex.guards._seals_checks_1_5.arun_cmd", new_callable=AsyncMock) as mock_run,
        patch("cortex.swarm.legion_vectors.EntropyDemon") as mock_demon,
        patch("cortex.swarm.legion_vectors.Intruder") as mock_intruder,
    ):
        mock_run.return_value = (0, "No issues")
        mock_demon.return_value.attack = AsyncMock(return_value=["Bare `except`"])
        mock_intruder.return_value.attack = AsyncMock(return_value=[])
        passed, _ = await check_seal_3_security()
        assert passed is False


# --- SEAL 4: TESTS ---


@pytest.mark.asyncio
async def test_seal_4_happy():
    with patch("cortex.guards._seals_checks_1_5.arun_cmd", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = (0, "All passed")
        passed, _ = await check_seal_4_tests()
        assert passed is True


@pytest.mark.asyncio
async def test_seal_4_rejection():
    with patch("cortex.guards._seals_checks_1_5.arun_cmd", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = (1, "Tests failed")
        passed, _ = await check_seal_4_tests()
        assert passed is False


@pytest.mark.asyncio
async def test_seal_4_timeout():
    with patch("cortex.guards._seals_checks_1_5.arun_cmd", new_callable=AsyncMock) as mock_run:
        mock_run.side_import = AsyncMock(
            side_effect=Exception("Timeout")
        )  # or simulate via wait_for

        async def mock_wait_for(coro, timeout):
            coro.close()
            raise pytest.importorskip("asyncio").TimeoutError()

        with patch("asyncio.wait_for", side_effect=mock_wait_for):
            passed, _ = await check_seal_4_tests()
            assert passed is False


# --- SEAL 5: LEDGER ---


@pytest.mark.asyncio
async def test_seal_5_happy():
    with (
        patch("cortex.engine.core.cortex_engine.CortexEngine", autospec=True) as mock_engine,
        patch("cortex.guards._seals_checks_1_5.arun_cmd", new_callable=AsyncMock) as mock_run,
    ):
        mock_run.return_value = (0, "Passed")
        passed, _ = await check_seal_5_ledger()
        assert passed is True


@pytest.mark.asyncio
async def test_seal_5_init_rejection():
    with (
        patch(
            "cortex.engine.core.cortex_engine.CortexEngine", side_effect=RuntimeError("DB Error")
        ),
        patch("cortex.guards._seals_checks_1_5.arun_cmd", new_callable=AsyncMock) as mock_run,
    ):
        mock_run.return_value = (0, "Passed")
        passed, _ = await check_seal_5_ledger()
        assert passed is False


@pytest.mark.asyncio
async def test_seal_5_guard_rejection():
    with (
        patch("cortex.engine.core.cortex_engine.CortexEngine", autospec=True) as mock_engine,
        patch("cortex.guards._seals_checks_1_5.arun_cmd", new_callable=AsyncMock) as mock_run,
    ):
        mock_run.return_value = (1, "Guard failed")
        passed, _ = await check_seal_5_ledger()
        assert passed is False


# --- SEAL 6: ASYNC & PERF ---


@pytest.mark.asyncio
async def test_seal_6_happy(mock_cache):
    mock_cache.files = {Path("ok.py"): "async def foo(): await asyncio.sleep(1)"}
    with (
        patch(
            "cortex.guards._seals_checks_6_10._check_temperature_determinism",
            AsyncMock(return_value=[]),
        ),
        patch(
            "cortex.guards._seals_checks_6_10._check_latency_telemetry", AsyncMock(return_value=[])
        ),
    ):
        passed, _ = await check_seal_6_async_perf()
        assert passed is True


@pytest.mark.asyncio
async def test_seal_6_sleep_rejection(mock_cache):
    mock_cache.files = {Path("bad.py"): "time.sleep(1)"}
    with (
        patch(
            "cortex.guards._seals_checks_6_10._check_temperature_determinism",
            AsyncMock(return_value=[]),
        ),
        patch(
            "cortex.guards._seals_checks_6_10._check_latency_telemetry", AsyncMock(return_value=[])
        ),
    ):
        passed, _ = await check_seal_6_async_perf()
        assert passed is False


@pytest.mark.asyncio
async def test_seal_6_temp_rejection(mock_cache):
    mock_cache.files = {Path("ok.py"): "code"}
    with (
        patch(
            "cortex.guards._seals_checks_6_10._check_temperature_determinism",
            AsyncMock(return_value=["router.py"]),
        ),
        patch(
            "cortex.guards._seals_checks_6_10._check_latency_telemetry", AsyncMock(return_value=[])
        ),
    ):
        passed, _ = await check_seal_6_async_perf()
        assert passed is False


# --- SEAL 7: AXIOM REGISTRY ---


@pytest.mark.asyncio
async def test_seal_7_happy():
    mock_registry = [1, 2, 3, 4, 5, 6, 7]
    with (
        patch("cortex_extensions.axioms.AXIOM_REGISTRY", mock_registry),
        patch("cortex_extensions.axioms.registry.enforced", return_value=mock_registry),
    ):
        passed, _ = await check_seal_7_axiom_registry()
        assert passed is True


@pytest.mark.asyncio
async def test_seal_7_registry_rejection():
    mock_registry = [1, 2, 3, 4, 5]  # Only 5 axioms
    with (
        patch("cortex_extensions.axioms.AXIOM_REGISTRY", mock_registry),
        patch("cortex_extensions.axioms.registry.enforced", return_value=mock_registry),
    ):
        passed, _ = await check_seal_7_axiom_registry()
        assert passed is False


@pytest.mark.asyncio
async def test_seal_7_prompt_size_warn(tmp_path):
    mock_registry = [1, 2, 3, 4, 5, 6, 7]
    with (
        patch("cortex_extensions.axioms.AXIOM_REGISTRY", mock_registry),
        patch("cortex_extensions.axioms.registry.enforced", return_value=mock_registry),
        patch("cortex.guards._seals_checks_6_10.ROOT_DIR", tmp_path),
    ):
        prompt_file = tmp_path / "SYSTEM_PROMPT.md"
        prompt_file.write_text("word " * 600)
        passed, _ = await check_seal_7_axiom_registry()
        assert passed is True  # Non-blocking warning


# --- SEAL 8, 9, 10 --- (using their impl mocks)


@pytest.mark.asyncio
async def test_seal_8_happy():
    with patch(
        "cortex.guards._seals_checks_6_10.check_seal_8_dependency_impl",
        AsyncMock(return_value=(True, "verified")),
    ):
        passed, _ = await check_seal_8_dependency()
        assert passed is True


@pytest.mark.asyncio
async def test_seal_9_happy():
    with patch(
        "cortex.guards._seals_checks_6_10.check_seal_9_compliance_impl",
        AsyncMock(return_value=(True, "verified")),
    ):
        passed, _ = await check_seal_9_compliance()
        assert passed is True


@pytest.mark.asyncio
async def test_seal_10_happy():
    with patch(
        "cortex.guards._seals_checks_6_10.check_gate_21_preservation",
        AsyncMock(return_value=(True, "verified")),
    ):
        passed, _ = await check_seal_10_preservation()
        assert passed is True


@pytest.mark.asyncio
async def test_seal_10_rejection():
    with patch(
        "cortex.guards._seals_checks_6_10.check_gate_21_preservation",
        AsyncMock(return_value=(False, "broken")),
    ):
        passed, _ = await check_seal_10_preservation()
        assert passed is False
