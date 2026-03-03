"""Tests for ScalingEngine — Automated Scaling (Ω₅)."""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from scripts.scaling_engine import ScalingEngine

@pytest.fixture
def vault():
    v = MagicMock()
    return v

@pytest.fixture
def engine(vault):
    return ScalingEngine(vault=vault)

@pytest.mark.asyncio
async def test_scaling_engine_provision_success(engine, vault):
    """Full successful registration + verification flow."""
    agent_name = "legion-test"
    
    mock_mail = AsyncMock()
    mock_mail.create_account.return_value = "test@domain.com"
    mock_mail.password = "pass123"
    mock_mail.wait_for_message.return_value = {
        "text": "Your verification code is 123456. Welcome!"
    }
    
    mock_client = AsyncMock()
    mock_client.register.return_value = {
        "agent": {"api_key": "sk_legion", "name": agent_name}
    }
    mock_client.submit_verification.return_value = {"success": True}
    
    with patch("scripts.scaling_engine.TempMail", return_value=mock_mail), \
         patch("scripts.scaling_engine.MoltbookClient", return_value=mock_client), \
         patch.object(engine, "_generate_name", return_value=agent_name):
        
        result = await engine.provision_one()
        
    assert result == agent_name
    # Verify client transitions
    mock_client.register.assert_called_once()
    mock_mail.wait_for_message.assert_called_once()
    # verify_resp check
    mock_client.submit_verification.assert_called_once_with(
        verification_code="email_verify", 
        answer="123456"
    )
    # Vault storage check
    vault.store_identity.assert_called_once()
    args, kwargs = vault.store_identity.call_args
    assert kwargs["name"] == agent_name
    assert kwargs["email"] == "test@domain.com"
    assert kwargs["claimed"] is True


@pytest.mark.asyncio
async def test_scaling_engine_verification_timeout(engine, vault):
    """Registration works, but verification email never arrives."""
    agent_name = "legion-timeout"
    
    mock_mail = AsyncMock()
    mock_mail.create_account.return_value = "slow@domain.com"
    mock_mail.wait_for_message.return_value = None # Timeout
    
    mock_client = AsyncMock()
    mock_client.register.return_value = {
        "agent": {"api_key": "sk_slow", "name": agent_name}
    }
    
    with patch("scripts.scaling_engine.TempMail", return_value=mock_mail), \
         patch("scripts.scaling_engine.MoltbookClient", return_value=mock_client), \
         patch.object(engine, "_generate_name", return_value=agent_name):
        
        result = await engine.provision_one()
        
    assert result == agent_name # Still returns name because registration passed
    # Submit verification should NOT be called
    mock_client.submit_verification.assert_not_called()
    # Vault should store as claimed=False
    vault.store_identity.assert_called_once()
    args, kwargs = vault.store_identity.call_args
    assert kwargs["claimed"] is False
    assert kwargs["metadata"]["status"] == "pending_verify"


@pytest.mark.asyncio
async def test_scaling_engine_registration_failure(engine, vault):
    """Flow breaks at registration."""
    mock_mail = AsyncMock()
    mock_client = AsyncMock()
    mock_client.register.return_value = {"error": "Name taken"}
    
    with patch("scripts.scaling_engine.TempMail", return_value=mock_mail), \
         patch("scripts.scaling_engine.MoltbookClient", return_value=mock_client):
        
        result = await engine.provision_one()
        
    assert result is None
    vault.store_identity.assert_not_called()
