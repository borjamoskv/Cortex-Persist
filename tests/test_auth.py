"""
CORTEX v5.0 — Auth Tests.

Tests for API key creation, authentication, and revocation.
"""

import os
import sqlite3
import tempfile

import pytest

from cortex.auth import AUTH_SCHEMA, AuthManager


@pytest.fixture
def auth():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db = tmp.name
    # Create the api_keys table before using AuthManager
    conn = sqlite3.connect(db)
    conn.executescript(AUTH_SCHEMA)
    conn.close()
    manager = AuthManager(db)
    yield manager
    os.unlink(db)


class TestKeyCreation:
    @pytest.mark.asyncio
    async def test_create_key(self, auth):
        raw_key, api_key = await auth.create_key("test-key")
        assert raw_key.startswith("ctx_")
        assert api_key.name == "test-key"
        assert api_key.is_active is True

    @pytest.mark.asyncio
    async def test_key_prefix_stored(self, auth):
        raw_key, api_key = await auth.create_key("prefix-test")
        assert api_key.key_prefix == raw_key[:12]

    @pytest.mark.asyncio
    async def test_custom_permissions(self, auth):
        _, api_key = await auth.create_key("readonly", permissions=["read"])
        assert api_key.permissions == ["read"]

    @pytest.mark.asyncio
    async def test_custom_tenant(self, auth):
        _, api_key = await auth.create_key("tenant-test", tenant_id="acme-corp")
        assert api_key.tenant_id == "acme-corp"


class TestAuthentication:
    @pytest.mark.asyncio
    async def test_valid_key(self, auth):
        raw_key, _ = await auth.create_key("auth-test")
        result = await auth.authenticate_async(raw_key)
        assert result.authenticated is True
        assert result.key_name == "auth-test"

    @pytest.mark.asyncio
    async def test_invalid_key(self, auth):
        result = await auth.authenticate_async("ctx_invalid_key_12345")
        assert result.authenticated is False

    @pytest.mark.asyncio
    async def test_bad_format(self, auth):
        result = await auth.authenticate_async("not-a-cortex-key")
        assert result.authenticated is False
        assert "format" in result.error.lower()

    @pytest.mark.asyncio
    async def test_empty_key(self, auth):
        result = await auth.authenticate_async("")
        assert result.authenticated is False


class TestRevocation:
    @pytest.mark.asyncio
    async def test_revoke_key(self, auth):
        raw_key, api_key = await auth.create_key("revoke-test")
        assert await auth.revoke_key(api_key.id) is True
        result = await auth.authenticate_async(raw_key)
        assert result.authenticated is False

    @pytest.mark.asyncio
    async def test_revoke_nonexistent(self, auth):
        assert await auth.revoke_key(99999) is False


class TestListKeys:
    @pytest.mark.asyncio
    async def test_list_all(self, auth):
        await auth.create_key("key-1")
        await auth.create_key("key-2")
        keys = await auth.list_keys()
        assert len(keys) == 2

    @pytest.mark.asyncio
    async def test_list_by_tenant(self, auth):
        await auth.create_key("t1", tenant_id="alpha")
        await auth.create_key("t2", tenant_id="beta")
        alpha_keys = await auth.list_keys(tenant_id="alpha")
        assert len(alpha_keys) == 1
        assert alpha_keys[0].tenant_id == "alpha"
