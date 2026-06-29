import json
import os
import urllib.error
from unittest.mock import patch

import pytest
from babylon60.guards.uptimebolt_guard import enforce_deploy_safety

@pytest.fixture
def mock_env():
    with patch.dict(os.environ, {"UPTIMEBOLT_API_KEY": "test-key"}):
        yield

def test_bypass_if_not_deploy():
    # Should not raise any exceptions
    enforce_deploy_safety(json.dumps({"fact_type": "knowledge"}))

def test_bypass_if_no_api_key():
    with patch.dict(os.environ, {}, clear=True):
        # Should not raise exception even if fact_type is deploy
        enforce_deploy_safety(json.dumps({"fact_type": "deploy"}))

@patch("urllib.request.urlopen")
def test_proceed_when_safe(mock_urlopen, mock_env):
    mock_response = mock_urlopen.return_value.__enter__.return_value
    mock_response.read.return_value = json.dumps({
        "result": {
            "content": [{"text": '{"recommendation": "proceed", "risk_level": "low"}'}]
        }
    }).encode("utf-8")
    
    # Should not raise exception
    enforce_deploy_safety(json.dumps({"fact_type": "deploy", "project": "test-service"}))

@patch("urllib.request.urlopen")
def test_reject_when_high_risk(mock_urlopen, mock_env):
    mock_response = mock_urlopen.return_value.__enter__.return_value
    mock_response.read.return_value = json.dumps({
        "result": {
            "content": [{"text": '{"recommendation": "wait_and_monitor", "risk_level": "high"}'}]
        }
    }).encode("utf-8")
    
    with pytest.raises(ValueError, match="SAGA-1 Rejection by UptimeBolt: Risk is HIGH"):
        enforce_deploy_safety(json.dumps({"fact_type": "deploy", "project": "test-service"}))

@patch("urllib.request.urlopen")
def test_fail_open_on_connection_error(mock_urlopen, mock_env):
    mock_urlopen.side_effect = urllib.error.URLError("Connection refused")
    
    # Should not raise exception
    enforce_deploy_safety(json.dumps({"fact_type": "deploy", "project": "test-service"}))
