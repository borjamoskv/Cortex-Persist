# [C5-REAL] Exergy-Maximized
import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from cortex.api.core import app

@pytest.fixture
def client():
    return TestClient(app)

def test_verify_webhook_fallback_success(client):
    """
    Test verifying webhook using default fallback token.
    """
    params = {
        "hub.mode": "subscribe",
        "hub.verify_token": "CORTEX_KAPSO_VERIFY_TOKEN",
        "hub.challenge": "123456"
    }
    # Ensure neither keyring nor environment variables are set
    with patch("babylon60.extensions.kapso.webhook.keyring", None):
        with patch.dict(os.environ, {"PYTEST_CURRENT_TEST": "true"}, clear=True):
            response = client.get("/kapso/webhook", params=params)
            assert response.status_code == 200
            assert response.json() == 123456

def test_verify_webhook_env_success(client):
    """
    Test verifying webhook using environment variable CORTEX_KAPSO_VERIFY_TOKEN.
    """
    params = {
        "hub.mode": "subscribe",
        "hub.verify_token": "env_verify_token_999",
        "hub.challenge": "654321"
    }
    with patch("babylon60.extensions.kapso.webhook.keyring", None):
        with patch.dict(os.environ, {"CORTEX_KAPSO_VERIFY_TOKEN": "env_verify_token_999", "PYTEST_CURRENT_TEST": "true"}, clear=True):
            response = client.get("/kapso/webhook", params=params)
            assert response.status_code == 200
            assert response.json() == 654321

def test_verify_webhook_keyring_success(client):
    """
    Test verifying webhook retrieving verify token from Keyring.
    """
    params = {
        "hub.mode": "subscribe",
        "hub.verify_token": "keyring_verify_token_xyz",
        "hub.challenge": "789012"
    }
    
    mock_keyring = MagicMock()
    mock_keyring.get_password.return_value = "keyring_verify_token_xyz"
    
    with patch("babylon60.extensions.kapso.webhook.keyring", mock_keyring):
        with patch.dict(os.environ, {"PYTEST_CURRENT_TEST": "true"}, clear=True):
            response = client.get("/kapso/webhook", params=params)
            assert response.status_code == 200
            assert response.json() == 789012
            mock_keyring.get_password.assert_called_once_with("cortex_v6", "kapso_verify_token")

def test_verify_webhook_keyring_error_fallback(client):
    """
    Test fallback to environment when keyring raised an exception.
    """
    params = {
        "hub.mode": "subscribe",
        "hub.verify_token": "fallback_token_from_env",
        "hub.challenge": "456789"
    }
    
    mock_keyring = MagicMock()
    mock_keyring.get_password.side_effect = Exception("Keyring unavailable")
    
    with patch("babylon60.extensions.kapso.webhook.keyring", mock_keyring):
        with patch.dict(os.environ, {"CORTEX_KAPSO_VERIFY_TOKEN": "fallback_token_from_env", "PYTEST_CURRENT_TEST": "true"}, clear=True):
            response = client.get("/kapso/webhook", params=params)
            assert response.status_code == 200
            assert response.json() == 456789

def test_verify_webhook_forbidden(client):
    """
    Test returns 403 when verify_token does not match.
    """
    params = {
        "hub.mode": "subscribe",
        "hub.verify_token": "wrong_token",
        "hub.challenge": "123456"
    }
    with patch("babylon60.extensions.kapso.webhook.keyring", None):
        with patch.dict(os.environ, {"PYTEST_CURRENT_TEST": "true"}, clear=True):
            response = client.get("/kapso/webhook", params=params)
            assert response.status_code == 403
            assert response.json() == {"detail": "Forbidden"}

def test_verify_webhook_bad_request(client):
    """
    Test returns 400 when query parameters are missing.
    """
    response = client.get("/kapso/webhook")
    assert response.status_code == 400
    assert response.json() == {"detail": "Bad Request"}

def test_receive_webhook_post_success(client):
    """
    Test POST endpoint receives webhook payload.
    """
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "12345",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "15550000000"
                            }
                        }
                    }
                ]
            }
        ]
    }
    response = client.post("/kapso/webhook", json=payload)
    assert response.status_code == 200
    assert response.json() == {"status": "received"}
