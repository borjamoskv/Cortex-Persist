"""Authentication package exports.

Keep package import lightweight so schema/manager consumers do not depend on
FastAPI dependency modules at import time.
"""

from __future__ import annotations

__all__: list[str] = []

try:
    from cortex.auth.manager import AuthManager, get_auth_manager, reset_auth_manager
except Exception:  # noqa: BLE001
    AuthManager = None  # type: ignore[assignment]
    get_auth_manager = None  # type: ignore[assignment]
    reset_auth_manager = None  # type: ignore[assignment]
else:
    __all__ += ["AuthManager", "get_auth_manager", "reset_auth_manager"]

try:
    from cortex.auth.models import APIKey, AuthResult
except Exception:  # noqa: BLE001
    APIKey = None  # type: ignore[assignment]
    AuthResult = None  # type: ignore[assignment]
else:
    __all__ += ["APIKey", "AuthResult"]

try:
    from cortex.auth.schema import AUTH_SCHEMA, SQL_INSERT_KEY
except Exception:  # noqa: BLE001
    AUTH_SCHEMA = None  # type: ignore[assignment]
    SQL_INSERT_KEY = None  # type: ignore[assignment]
else:
    __all__ += ["AUTH_SCHEMA", "SQL_INSERT_KEY"]

try:
    from cortex.auth.deps import (
        require_auth,
        require_consensus,
        require_permission,
        require_verified_permission,
    )
except Exception:  # noqa: BLE001
    require_auth = None  # type: ignore[assignment]
    require_consensus = None  # type: ignore[assignment]
    require_permission = None  # type: ignore[assignment]
    require_verified_permission = None  # type: ignore[assignment]
else:
    __all__ += [
        "require_auth",
        "require_consensus",
        "require_permission",
        "require_verified_permission",
    ]
