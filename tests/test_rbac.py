from unittest.mock import Mock

import pytest
from fastapi import Request

from cortex.auth import AuthResult, require_permission
from cortex.auth.rbac import Permission


@pytest.mark.asyncio
async def test_rbac_permission_enum():
    """Test that require_permission works with Permission enums."""
    # Mocking Request and AuthResult
    mock_request = Mock(spec=Request)
    mock_request.headers = {"Accept-Language": "en"}

    # 1. Admin should have READ_FACTS (by hierarchy or policy)
    auth_admin = AuthResult(authenticated=True, role="admin", permissions=[])
    checker = require_permission(Permission.READ_FACTS)
    result = await checker(mock_request, auth_admin)
    assert result == auth_admin

    # 2. Viewer should have READ_FACTS
    auth_viewer = AuthResult(authenticated=True, role="viewer", permissions=[])
    result = await checker(mock_request, auth_viewer)
    assert result == auth_viewer

    # 3. Viewer should NOT have MANAGE_KEYS
    checker_manage = require_permission(Permission.MANAGE_KEYS)
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        await checker_manage(mock_request, auth_viewer)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_legacy_string_permission():
    """Test that legacy string permissions still work."""
    mock_request = Mock(spec=Request)
    mock_request.headers = {"Accept-Language": "en"}

    auth = AuthResult(authenticated=True, role="user", permissions=["legacy_perm"])
    checker = require_permission("legacy_perm")
    result = await checker(mock_request, auth)
    assert result == auth

    checker_fail = require_permission("missing_perm")
    from fastapi import HTTPException

    with pytest.raises(HTTPException):
        await checker_fail(mock_request, auth)
