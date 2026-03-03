
import pytest
import asyncio
from unittest.mock import MagicMock, patch
from pathlib import Path
import json
import sqlite3
from moltbook.identity_vault import IdentityVault
from scripts.mass_registration_attack import get_proxies, register_with_proxy

@pytest.fixture
def temp_vault(tmp_path):
    """Fixture for an in-memory IdentityVault."""
    db_path = tmp_path / "test_identities.db"
    vault = IdentityVault(db_path=str(db_path))
    return vault

class TestIdentityVault:
    def test_init_db(self, temp_vault):
        assert Path(temp_vault.db_path).exists()
        with sqlite3.connect(temp_vault.db_path) as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='identities'")
            assert cursor.fetchone() is not None

    def test_store_and_get_identity(self, temp_vault):
        temp_vault.store_identity(
            name="TestAgent",
            api_key="sk-test-123",
            email="test@example.com",
            metadata={"test": "data"}
        )
        
        identity = temp_vault.get_identity("TestAgent")
        assert identity["name"] == "TestAgent"
        assert identity["api_key"] == "sk-test-123"
        assert identity["email"] == "test@example.com"
        assert identity["metadata"]["test"] == "data"

    def test_list_identities(self, temp_vault):
        temp_vault.store_identity("Agent1", "key1", claimed=True)
        temp_vault.store_identity("Agent2", "key2", claimed=False)
        
        all_ids = temp_vault.list_identities()
        assert len(all_ids) == 2
        
        claimed_ids = temp_vault.list_identities(claimed_only=True)
        assert len(claimed_ids) == 1
        assert claimed_ids[0]["name"] == "Agent1"

class TestRegistrationLogic:
    @pytest.mark.asyncio
    @patch("httpx.AsyncClient.get")
    async def test_get_proxies(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.text = "1.2.3.4:8080\n5.6.7.8:9090"
        mock_get.return_value = mock_resp
        
        proxies = await get_proxies()
        assert len(proxies) == 2
        assert "socks4://1.2.3.4:8080" in proxies

    @pytest.mark.asyncio
    @patch("moltbook.client.MoltbookClient.register")
    @patch("moltbook.client.MoltbookClient.close")
    async def test_register_with_proxy_success(self, mock_close, mock_register, temp_vault):
        mock_register.return_value = {
            "agent": {
                "api_key": "new-api-key",
                "claim_url": "https://www.moltbook.com/claim/test"
            }
        }
        
        result = await register_with_proxy("Dron-1", "socks4://1.1.1.1:1111", temp_vault)
        
        assert result["api_key"] == "new-api-key"
        identity = temp_vault.get_identity("Dron-1")
        assert identity is not None
        assert identity["api_key"] == "new-api-key"
        assert identity["metadata"]["proxy_used"] == "socks4://1.1.1.1:1111"

    @pytest.mark.asyncio
    @patch("moltbook.client.MoltbookClient.register")
    @patch("moltbook.client.MoltbookClient.close")
    async def test_register_with_proxy_failure(self, mock_close, mock_register, temp_vault):
        mock_register.side_effect = Exception("Moltbook Error")
        
        result = await register_with_proxy("Dron-1", "socks4://1.1.1.1:1111", temp_vault)
        
        assert result is None
        assert temp_vault.get_identity("Dron-1") is None

class TestZeroTrustAsalto:
    """Security verification for the assault logic."""
    
    def test_no_hardcoded_keys(self):
        script_path = Path("/Users/borjafernandezangulo/cortex/scripts/mass_registration_attack.py")
        content = script_path.read_text()
        # Ensure no "moltbook_sk_" or similar hardcoded in the script
        assert "moltbook_sk_" not in content
        assert "api_key =" not in content or "agent[" in content # only dynamic access
