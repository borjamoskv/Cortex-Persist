import pytest
from unittest.mock import patch, MagicMock
from cortex.engine.logic.atms import AtmsAdapter

def test_atms_adapter_cortex_rs_missing():
    """Verify that AtmsAdapter falls back correctly when cortex_rs is missing."""
    with patch("cortex.engine.logic.atms.cortex_rs", None):
        with pytest.raises(RuntimeError, match="cortex_rs PyO3 extension is required for ATMS operations"):
            AtmsAdapter()

def test_atms_adapter_cortex_rs_missing_atmsgraph():
    """Verify that AtmsAdapter falls back correctly when cortex_rs is missing AtmsGraph."""
    mock_cortex_rs = MagicMock()
    del mock_cortex_rs.AtmsGraph
    with patch("cortex.engine.logic.atms.cortex_rs", mock_cortex_rs):
        with pytest.raises(RuntimeError, match="cortex_rs PyO3 extension is missing AtmsGraph"):
            AtmsAdapter()
