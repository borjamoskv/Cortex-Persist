# [C5-REAL] Exergy-Maximized
"""
Comprehensive tests for cortex.auth module.

Covers:
  - AuthManager: create_key, authenticate_async, list_keys, revoke_key, close
  - SQLiteAuthBackend: full CRUD lifecycle
  - RBAC: Permission hierarchy, RBACEvaluator, authorize
  - PermissionCache: get/set, TTL expiry, capacity eviction
  - Models: APIKey / AuthResult dataclass shapes
"""

from __future__ import annotations

import asyncio
import time
from unittest.mock import patch

import aiosqlite
import pytest

from babylon60.auth.manager import AuthManager, reset_auth_manager
from babylon60.auth.models import APIKey, AuthResult
from babylon60.auth.rbac import (
    DEFAULT_POLICIES,
    RBAC,
    Permission,
    RBACEvaluator,
    Role,
    ROLE_HIERARCHY,
)
from babylon60.auth.cache import AUTH_CACHE, CacheEntry, PermissionCache


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
async def auth_manager(tmp_path):
    """Provides an initialized AuthManager backed by a fresh SQLite DB."""
    db_path = str(tmp_path / "auth_test.db")
    manager = AuthManager(db_path)
    await manager.initialize()
    yield manager
    await manager.close()


@pytest.fixture(autouse=True)
def reset_global_auth():
    """Reset the global singleton before each test."""
    reset_auth_manager()
    yield
    reset_auth_manager()


# ── AuthManager Tests ─────────────────────────────────────────────────────────


class TestAuthManager:
    """Test suite for the core AuthManager."""

    @pytest.mark.asyncio
    async def test_create_key_returns_raw_and_metadata(self, auth_manager):
        """create_key must return (raw_key, APIKey) tuple."""
        raw, key = await auth_manager.create_key("test-key", tenant_id="t1")
        assert isinstance(raw, str)
        assert raw.startswith("ctx_")
        assert isinstance(key, APIKey)
        assert key.name == "test-key"
        assert key.tenant_id == "t1"
        assert key.is_active is True

    @pytest.mark.asyncio
    async def test_create_key_raw_length(self, auth_manager):
        """Raw key must be ctx_ + 64 hex chars (32 bytes)."""
        raw, _ = await auth_manager.create_key("len-key")
        assert raw.startswith("ctx_")
        assert len(raw) == 4 + 64  # "ctx_" + 64 hex chars

    @pytest.mark.asyncio
    async def test_create_key_default_permissions(self, auth_manager):
        """Default permissions must be ['read', 'write']."""
        _, key = await auth_manager.create_key("default-perm-key")
        assert key.permissions == ["read", "write"]

    @pytest.mark.asyncio
    async def test_create_key_custom_permissions(self, auth_manager):
        """Custom permissions should be stored and returned."""
        _, key = await auth_manager.create_key("custom-key", permissions=["read", "admin"])
        assert key.permissions == ["read", "admin"]

    @pytest.mark.asyncio
    async def test_create_key_custom_role(self, auth_manager):
        """Custom role must be stored correctly."""
        _, key = await auth_manager.create_key("admin-key", role="admin")
        assert key.role == "admin"

    @pytest.mark.asyncio
    async def test_create_key_custom_rate_limit(self, auth_manager):
        """rate_limit should be stored and returned."""
        _, key = await auth_manager.create_key("rate-key", rate_limit=500)
        assert key.rate_limit == 500

    @pytest.mark.asyncio
    async def test_authenticate_valid_key(self, auth_manager):
        """authenticate_async with a valid key must return authenticated=True."""
        raw, _ = await auth_manager.create_key("auth-key", tenant_id="t-auth")
        result = await auth_manager.authenticate_async(raw)
        assert result.authenticated is True
        assert result.tenant_id == "t-auth"
        assert result.key_name == "auth-key"
        assert result.error == ""

    @pytest.mark.asyncio
    async def test_authenticate_invalid_format(self, auth_manager):
        """Keys not starting with 'ctx_' must be rejected."""
        result = await auth_manager.authenticate_async("bad_key_format_here")
        assert result.authenticated is False
        assert "format" in result.error.lower()

    @pytest.mark.asyncio
    async def test_authenticate_empty_key(self, auth_manager):
        """Empty string key must fail authentication."""
        result = await auth_manager.authenticate_async("")
        assert result.authenticated is False

    @pytest.mark.asyncio
    async def test_authenticate_wrong_key(self, auth_manager):
        """A well-formed but non-existent key must fail."""
        result = await auth_manager.authenticate_async("ctx_" + "a" * 64)
        assert result.authenticated is False
        assert "invalid" in result.error.lower() or "revoked" in result.error.lower()

    @pytest.mark.asyncio
    async def test_authenticate_returns_permissions(self, auth_manager):
        """Authenticated result must carry the key's permissions."""
        raw, _ = await auth_manager.create_key("perm-key", permissions=["read", "write", "admin"])
        result = await auth_manager.authenticate_async(raw)
        assert result.authenticated is True
        assert "read" in result.permissions
        assert "admin" in result.permissions

    @pytest.mark.asyncio
    async def test_authenticate_returns_role(self, auth_manager):
        """Authenticated result must carry the key's role."""
        raw, _ = await auth_manager.create_key("role-key", role="agent")
        result = await auth_manager.authenticate_async(raw)
        assert result.role == "agent"

    @pytest.mark.asyncio
    async def test_list_keys_all(self, auth_manager):
        """list_keys without tenant filter must return all keys."""
        await auth_manager.create_key("k1", tenant_id="t1")
        await auth_manager.create_key("k2", tenant_id="t2")
        keys = await auth_manager.list_keys()
        assert len(keys) == 2
        names = {k.name for k in keys}
        assert names == {"k1", "k2"}

    @pytest.mark.asyncio
    async def test_list_keys_by_tenant(self, auth_manager):
        """list_keys with tenant filter must scope results."""
        await auth_manager.create_key("k1", tenant_id="alpha")
        await auth_manager.create_key("k2", tenant_id="beta")
        keys = await auth_manager.list_keys(tenant_id="alpha")
        assert len(keys) == 1
        assert keys[0].name == "k1"

    @pytest.mark.asyncio
    async def test_list_keys_returns_apikey_objects(self, auth_manager):
        """list_keys must return a list of APIKey dataclass instances."""
        await auth_manager.create_key("dc-key")
        keys = await auth_manager.list_keys()
        assert all(isinstance(k, APIKey) for k in keys)

    @pytest.mark.asyncio
    async def test_revoke_key_succeeds(self, auth_manager):
        """revoke_key on existing key must return True."""
        _, key = await auth_manager.create_key("revoke-key")
        result = await auth_manager.revoke_key(key.id)
        assert result is True

    @pytest.mark.asyncio
    async def test_revoke_key_prevents_auth(self, auth_manager):
        """A revoked key must fail authentication."""
        raw, key = await auth_manager.create_key("revoke-auth-key")
        await auth_manager.revoke_key(key.id)
        result = await auth_manager.authenticate_async(raw)
        assert result.authenticated is False

    @pytest.mark.asyncio
    async def test_revoke_nonexistent_key(self, auth_manager):
        """revoke_key on non-existent ID must return False."""
        result = await auth_manager.revoke_key(99999)
        assert result is False

    @pytest.mark.asyncio
    async def test_key_prefix_stored(self, auth_manager):
        """The key_prefix (first 12 chars) must be stored."""
        raw, key = await auth_manager.create_key("prefix-key")
        assert key.key_prefix == raw[:12]

    @pytest.mark.asyncio
    async def test_hash_key_is_sha256(self, auth_manager):
        """hash_key_legacy_sha256 must produce a SHA-256 hex digest."""
        import hashlib

        test_key = "ctx_test123"
        expected = hashlib.sha256(test_key.encode()).hexdigest()
        assert AuthManager.hash_key_legacy_sha256(test_key) == expected

    @pytest.mark.asyncio
    async def test_multiple_keys_unique_ids(self, auth_manager):
        """Each created key must have a unique ID."""
        _, k1 = await auth_manager.create_key("unique1")
        _, k2 = await auth_manager.create_key("unique2")
        assert k1.id != k2.id

    @pytest.mark.asyncio
    async def test_close_idempotent(self, auth_manager):
        """Calling close() multiple times must not raise."""
        await auth_manager.close()
        await auth_manager.close()  # Should not raise

    @pytest.mark.asyncio
    async def test_authenticate_timing_uniformity(self, auth_manager):
        """Verify that invalid prefixes and invalid suffixes have uniform timing."""
        import time

        # 1. Non-existent key (invalid prefix)
        dur_invalid_prefix = float("inf")
        for _ in range(3):
            t0 = time.perf_counter()
            await auth_manager.authenticate_async("ctx_" + "a" * 64)
            t1 = time.perf_counter()
            dur_invalid_prefix = min(dur_invalid_prefix, t1 - t0)

        # 2. Key with valid prefix but invalid suffix
        raw, _ = await auth_manager.create_key("timing-key")
        valid_prefix = raw[:12]
        bad_suffix_key = valid_prefix + "b" * (len(raw) - 12)

        dur_invalid_suffix = float("inf")
        for _ in range(3):
            t2 = time.perf_counter()
            await auth_manager.authenticate_async(bad_suffix_key)
            t3 = time.perf_counter()
            dur_invalid_suffix = min(dur_invalid_suffix, t3 - t2)

        # The difference should be extremely small (typically < 150ms depending on CPU load)
        diff = abs(dur_invalid_prefix - dur_invalid_suffix)
        assert diff < 0.15, f"Timing difference too large: {diff:.4f}s"

    @pytest.mark.asyncio
    async def test_authenticate_negative_cases(self, auth_manager):
        """Verify negative authentication scenarios and fuzzing inputs."""
        # Nonexistent key
        res = await auth_manager.authenticate_async(
            "ctx_nonexistentkeyvalue12345678901234567890123456789012345678"
        )
        assert res.authenticated is False

        # Correct prefix, incorrect suffix
        raw, _ = await auth_manager.create_key("negative-test-key")
        bad_key = raw[:12] + "0" * (len(raw) - 12)
        res = await auth_manager.authenticate_async(bad_key)
        assert res.authenticated is False

        # Incorrect prefix
        res = await auth_manager.authenticate_async("ctx_incorrectprefix_12345")
        assert res.authenticated is False

        # Empty string key
        res = await auth_manager.authenticate_async("")
        assert res.authenticated is False

        # Unicode characters in key
        res = await auth_manager.authenticate_async("ctx_ññóíúá_12345")
        assert res.authenticated is False

        # Gigantic key (100,000 characters)
        giant_key = "ctx_" + "a" * 100000
        res = await auth_manager.authenticate_async(giant_key)
        assert res.authenticated is False


# ── RBAC Tests ────────────────────────────────────────────────────────────────


class TestRBAC:
    """Test suite for Role-Based Access Control."""

    def test_admin_can_read_facts(self):
        assert RBAC.has_permission("admin", Permission.READ_FACTS) is True

    def test_admin_can_manage_keys(self):
        assert RBAC.has_permission("admin", Permission.MANAGE_KEYS) is True

    def test_viewer_can_read(self):
        assert RBAC.has_permission("viewer", Permission.READ_FACTS) is True

    def test_viewer_cannot_write(self):
        assert RBAC.has_permission("viewer", Permission.WRITE_FACTS) is False

    def test_viewer_cannot_delete(self):
        assert RBAC.has_permission("viewer", Permission.DELETE_FACTS) is False

    def test_viewer_cannot_manage_keys(self):
        assert RBAC.has_permission("viewer", Permission.MANAGE_KEYS) is False

    def test_agent_can_write(self):
        assert RBAC.has_permission("agent", Permission.WRITE_FACTS) is True

    def test_agent_can_search(self):
        assert RBAC.has_permission("agent", Permission.SEARCH) is True

    def test_agent_cannot_purge(self):
        assert RBAC.has_permission("agent", Permission.PURGE_DATA) is False

    def test_system_has_all_permissions(self):
        """System role must have every defined permission."""
        for perm in Permission:
            assert RBAC.has_permission("system", perm) is True, f"system missing {perm}"

    def test_unknown_role_denied(self):
        """Unknown roles must always be denied."""
        assert RBAC.has_permission("hacker", Permission.READ_FACTS) is False

    def test_authorize_raises_on_denial(self):
        """authorize() must raise PermissionDeniedError on missing permission."""
        from babylon60.utils.errors import PermissionDeniedError

        with pytest.raises(PermissionDeniedError):
            RBAC.authorize("viewer", Permission.WRITE_FACTS)

    def test_authorize_passes_on_grant(self):
        """authorize() must not raise when permission is granted."""
        RBAC.authorize("admin", Permission.READ_FACTS)  # Should not raise

    def test_role_hierarchy_system_includes_all(self):
        """SYSTEM role hierarchy must include all sub-roles."""
        assert ROLE_HIERARCHY[Role.SYSTEM] == {Role.SYSTEM, Role.ADMIN, Role.AGENT, Role.VIEWER}

    def test_role_hierarchy_admin_no_system(self):
        """ADMIN hierarchy must NOT include SYSTEM."""
        assert Role.SYSTEM not in ROLE_HIERARCHY[Role.ADMIN]

    def test_custom_evaluator(self):
        """Custom RBACEvaluator with custom policies works correctly."""
        custom = RBACEvaluator(
            {
                Role.VIEWER: {Permission.WRITE_FACTS},  # unusual but valid
            }
        )
        assert custom.has_permission("viewer", Permission.WRITE_FACTS) is True
        assert custom.has_permission("viewer", Permission.READ_FACTS) is False

    def test_permission_enum_values(self):
        """Verify Permission enum string values match expected format."""
        assert Permission.READ_FACTS.value == "read:facts"
        assert Permission.WRITE_FACTS.value == "write:facts"
        assert Permission.MANAGE_KEYS.value == "manage:keys"

    def test_role_enum_values(self):
        """Verify Role enum string values."""
        assert Role.ADMIN.value == "admin"
        assert Role.AGENT.value == "agent"
        assert Role.VIEWER.value == "viewer"
        assert Role.SYSTEM.value == "system"


# ── PermissionCache Tests ────────────────────────────────────────────────────


class TestPermissionCache:
    """Test suite for the auth permission cache."""

    def test_get_miss(self):
        cache = PermissionCache()
        assert cache.get("nonexistent", "tenant-1") is None

    def test_set_and_get(self):
        cache = PermissionCache()
        cache.set("claim-1", "tenant-1", 2.5)
        assert cache.get("claim-1", "tenant-1") == 2.5

    def test_tenant_isolation(self):
        """Cache entries must be scoped per tenant."""
        cache = PermissionCache()
        cache.set("claim-x", "tenant-a", 1.0)
        cache.set("claim-x", "tenant-b", 2.0)
        assert cache.get("claim-x", "tenant-a") == 1.0
        assert cache.get("claim-x", "tenant-b") == 2.0

    def test_ttl_expiry(self):
        """Expired entries must return None."""
        cache = PermissionCache()
        entry = CacheEntry(value=42, timestamp=time.monotonic() - 120.0, ttl=60.0)
        cache._data["test-tenant:claim"] = entry
        assert cache.get("claim", "test-tenant") is None

    def test_capacity_eviction(self):
        """When capacity is exceeded, cache must evict."""
        cache = PermissionCache(capacity=3)
        cache.set("a", "t", 1)
        cache.set("b", "t", 2)
        cache.set("c", "t", 3)
        # This should trigger eviction (clear all)
        cache.set("d", "t", 4)
        # After clear + new insert, only "d" should remain
        assert cache.get("d", "t") == 4
        assert cache.get("a", "t") is None

    def test_overwrite_existing(self):
        """Setting the same key should overwrite."""
        cache = PermissionCache()
        cache.set("claim", "tenant", 1.0)
        cache.set("claim", "tenant", 2.0)
        assert cache.get("claim", "tenant") == 2.0


# ── Model Tests ──────────────────────────────────────────────────────────────


class TestModels:
    """Test suite for auth data models."""

    def test_apikey_dataclass(self):
        key = APIKey(
            id=1,
            name="test",
            key_prefix="ctx_abc",
            tenant_id="t1",
            role="admin",
            permissions=["read", "write"],
            created_at="2026-01-01T00:00:00Z",
            last_used=None,
            is_active=True,
            rate_limit=100,
        )
        assert key.id == 1
        assert key.name == "test"
        assert key.is_active is True
        assert key.last_used is None

    def test_auth_result_success(self):
        result = AuthResult(
            authenticated=True,
            tenant_id="t1",
            role="admin",
            permissions=["read"],
            key_name="my-key",
        )
        assert result.authenticated is True
        assert result.error == ""

    def test_auth_result_failure(self):
        result = AuthResult(authenticated=False, error="Invalid key")
        assert result.authenticated is False
        assert result.tenant_id == "default"  # default value
        assert result.error == "Invalid key"

    def test_auth_result_defaults(self):
        result = AuthResult(authenticated=False)
        assert result.tenant_id == "default"
        assert result.role == "user"
        assert result.permissions == []
        assert result.key_name == ""
        assert result.error == ""
