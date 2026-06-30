# [C5-REAL] Exergy-Maximized
"""Authentication package exports.

Keep package import lightweight so schema/manager consumers do not depend on
FastAPI dependency modules at import time.
"""

from __future__ import annotations

__all__: list[str] = []

try:
    from babylon60.auth.manager import AuthManager, get_auth_manager, reset_auth_manager
except ImportError:
    AuthManager = None  # type: ignore[assignment]
    get_auth_manager = None  # type: ignore[assignment]
    reset_auth_manager = None  # type: ignore[assignment]
else:
    __all__ += ["AuthManager", "get_auth_manager", "reset_auth_manager"]

try:
    from babylon60.auth.models import APIKey, AuthResult
except ImportError:
    APIKey = None  # type: ignore[assignment]
    AuthResult = None  # type: ignore[assignment]
else:
    __all__ += ["APIKey", "AuthResult"]

try:
    from babylon60.auth.schema import AUTH_SCHEMA, SQL_INSERT_KEY
except ImportError:
    AUTH_SCHEMA = None  # type: ignore[assignment]
    SQL_INSERT_KEY = None  # type: ignore[assignment]
else:
    __all__ += ["AUTH_SCHEMA", "SQL_INSERT_KEY"]

try:
    from babylon60.auth.deps import (
        require_auth,
        require_consensus,
        require_permission,
        require_verified_permission,
    )
except ImportError:
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
