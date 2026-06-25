# [C5-REAL] Exergy-Maximized
import pytest
from unittest.mock import MagicMock
from legacy_research.guards.ctre_guard import CTREGuard, CTRECollisionError, HAS_RUST_CTRE
from legacy_research.engine.store_validation import run_store_validation_logic
from legacy_research.engine.store_mixin import StoreMixin


def test_ctre_collision_error_properties() -> None:
    err = CTRECollisionError(expected=12345, current=67890, epsilon=15)
    assert err.expected_hash == 12345
    assert err.current_hash == 67890
    assert err.epsilon == 15
    assert "CTRE SAGA ABORT" in str(err)


def test_ctre_guard_python_fallback() -> None:
    success, epsilon = CTREGuard._python_fallback(100, 100)
    assert success is True
    assert isinstance(epsilon, int)

    success, epsilon = CTREGuard._python_fallback(100, 200)
    assert success is False
    assert isinstance(epsilon, int)


def test_ctre_guard_validate_commit() -> None:
    # This calls either FFI or Python fallback depending on compilation
    success, epsilon = CTREGuard.validate_commit(999, 999)
    assert success is True
    assert isinstance(epsilon, int)

    success, epsilon = CTREGuard.validate_commit(999, 888)
    assert success is False
    assert isinstance(epsilon, int)


@pytest.mark.asyncio
async def test_store_validation_runs_ctre() -> None:
    # If the metadata contains UI_ACTION but hashes match, validation passes
    # We mock out mixin_instance and other guards to isolate CTRE validation
    mixin = MagicMock()
    conn = MagicMock()

    # Pass case: hashes match
    meta = {"intent": "UI_ACTION", "expected_ui_hash": 1234, "current_ui_hash": 1234}

    # run_store_validation_logic will process the metadata. We mock all subsequent validation
    # calls to avoid running other checks that require database connections.
    import legacy_research.engine.store_validation as sv
    import sys

    # Save original functions to restore later
    orig_dep = getattr(sv, "_validate_dependencies", None)
    orig_byz = getattr(sv, "_check_byzantine_auth", None)
    orig_thermo = getattr(sv, "_enforce_thermodynamics", None)
    orig_exergy = getattr(sv, "_apply_exergy", None)
    orig_dedup = getattr(sv, "_apply_semantic_dedup", None)
    orig_sanitize = getattr(sv, "_sanitize_engram", None)
    orig_privacy = getattr(mixin, "_apply_privacy_shield", None)

    async def mock_noop(*args, **kwargs):
        return None

    async def mock_noop_dedup(*args, **kwargs):
        return None, args[8], args[2], args[4]

    def mock_noop_sync(*args, **kwargs):
        return None

    def mock_sanitize(content, fact_type, source, project, meta):
        return content, meta

    sv._validate_dependencies = mock_noop_sync
    sv._check_byzantine_auth = mock_noop
    sv._enforce_thermodynamics = mock_noop_sync
    sv._apply_exergy = mock_noop_sync
    sv._apply_semantic_dedup = mock_noop_dedup
    sv._sanitize_engram = mock_sanitize
    mixin._apply_privacy_shield = lambda content, project, meta: meta

    try:
        # Expected match: no error raised
        dedupe_id, out_meta, out_content, out_fact_type = await run_store_validation_logic(
            mixin_instance=mixin,
            conn=conn,
            project="test-project",
            content="Click button",
            tenant_id="tenant-1",
            fact_type="action",
            tags=[],
            confidence="stated",
            source="agent:vlm",
            meta=meta,
        )
        assert out_meta["expected_ui_hash"] == 1234

        # Mismatch case: CTRECollisionError raised
        mismatch_meta = {"intent": "UI_ACTION", "expected_ui_hash": 1234, "current_ui_hash": 9999}
        with pytest.raises(CTRECollisionError) as exc_info:
            await run_store_validation_logic(
                mixin_instance=mixin,
                conn=conn,
                project="test-project",
                content="Click button",
                tenant_id="tenant-1",
                fact_type="action",
                tags=[],
                confidence="stated",
                source="agent:vlm",
                meta=mismatch_meta,
            )
        assert exc_info.value.expected_hash == 1234
        assert exc_info.value.current_hash == 9999

    finally:
        # Restore original functions
        if orig_dep:
            sv._validate_dependencies = orig_dep
        if orig_byz:
            sv._check_byzantine_auth = orig_byz
        if orig_thermo:
            sv._enforce_thermodynamics = orig_thermo
        if orig_exergy:
            sv._apply_exergy = orig_exergy
        if orig_dedup:
            sv._apply_semantic_dedup = orig_dedup
        if orig_sanitize:
            sv._sanitize_engram = orig_sanitize
