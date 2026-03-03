import pytest
from unittest.mock import MagicMock, patch

from cortex.engine.apotheosis import ApotheosisEngine
from cortex.engine.endocrine import HormoneType


@pytest.fixture
def mock_metamemory():
    metamemory = MagicMock()
    return metamemory


@pytest.fixture
def mock_cortex(mock_metamemory):
    cortex = MagicMock()
    manager = MagicMock()
    manager.metamemory = mock_metamemory
    cortex._memory_manager = manager
    return cortex


@pytest.fixture
def engine(mock_cortex, tmp_path):
    # Pass a valid path and mock engine
    return ApotheosisEngine(workspace=tmp_path, cortex_engine=mock_cortex)


@pytest.mark.asyncio
@patch("cortex.engine.apotheosis.ENDOCRINE")
async def test_metamemory_audit_high_brier_score_pulses_cortisol(mock_endocrine, engine, mock_metamemory):
    # Simulate high calibration drift (overconfidence/underconfidence)
    mock_metamemory.calibration_score.return_value = 0.40

    await engine._metamemory_audit()

    # Brier score > 0.25 should pulse Cortisol
    mock_endocrine.pulse.assert_called_once_with(
        HormoneType.CORTISOL,
        +0.10,
        reason="CalibrationDrift:0.40",
    )


@pytest.mark.asyncio
@patch("cortex.engine.apotheosis.ENDOCRINE")
async def test_metamemory_audit_optimal_calibration_pulses_dopamine(mock_endocrine, engine, mock_metamemory):
    # Simulate excellent calibration
    mock_metamemory.calibration_score.return_value = 0.15

    await engine._metamemory_audit()

    # Brier score <= 0.25 should pulse Dopamine
    mock_endocrine.pulse.assert_called_once_with(HormoneType.DOPAMINE, +0.02)


@pytest.mark.asyncio
@patch("cortex.engine.apotheosis.ENDOCRINE")
async def test_metamemory_audit_insufficient_data(mock_endocrine, engine, mock_metamemory):
    # -1.0 indicates insufficient data for Brier score
    mock_metamemory.calibration_score.return_value = -1.0

    await engine._metamemory_audit()

    # Should not pulse anything
    mock_endocrine.pulse.assert_not_called()
