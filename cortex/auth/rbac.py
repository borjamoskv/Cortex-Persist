"""
CORTEX v6 — Role-Based Access Control (RBAC) Engine.

Defines roles, permissions, and the evaluation logic for secure
multi-tenancy and agentic sovereignty.
"""

import logging
from enum import Enum

from cortex.utils.errors import PermissionDeniedError

logger = logging.getLogger("cortex.auth.rbac")


class Permission(str, Enum):
    """Atomic permissions in CORTEX."""

    # Data Access
    READ_FACTS = "read:facts"
    WRITE_FACTS = "write:facts"
    DELETE_FACTS = "delete:facts"
    PURGE_DATA = "purge:data"
    SEARCH = "search"
    SYNC = "sync"
    VIEW_LOGS = "view:logs"

    # System Management
    MANAGE_KEYS = "manage:keys"
    SYSTEM_CONFIG = "system:config"
    CONSENSUS_OVERRIDE = "consensus:override"
    SNAPSHOT_EXPORT = "snapshot:export"


class Role(str, Enum):
    """Predefined roles in the CORTEX ecosystem."""

    ADMIN = "admin"
    AGENT = "agent"
    VIEWER = "viewer"
    SYSTEM = "system"


# Role Hierarchy: SYSTEM > ADMIN > AGENT > VIEWER
# Higher roles include all permissions from lower roles.
ROLE_HIERARCHY: dict[Role, set[Role]] = {
    Role.ADMIN: {Role.ADMIN, Role.AGENT, Role.VIEWER},
    Role.AGENT: {Role.AGENT, Role.VIEWER},
    Role.VIEWER: {Role.VIEWER},
    Role.SYSTEM: {Role.SYSTEM, Role.ADMIN, Role.AGENT, Role.VIEWER},
}

DEFAULT_POLICIES: dict[Role, set[Permission]] = {
    Role.VIEWER: {
        Permission.READ_FACTS,
        Permission.SEARCH,
    },
    Role.AGENT: {
        Permission.READ_FACTS,
        Permission.WRITE_FACTS,
        Permission.DELETE_FACTS,
        Permission.SEARCH,
        Permission.SYNC,
    },
    Role.ADMIN: {
        Permission.READ_FACTS,
        Permission.WRITE_FACTS,
        Permission.DELETE_FACTS,
        Permission.SEARCH,
        Permission.SYNC,
        Permission.PURGE_DATA,
        Permission.MANAGE_KEYS,
        Permission.VIEW_LOGS,
    },
    Role.SYSTEM: set(Permission),
}


class RBACEvaluator:
    """Evaluates permissions based on roles and policies.

    Supports role hierarchy and explicit policy definitions.
    """

    def __init__(self, policies: dict[Role, set[Permission]] | None = None) -> None:
        self._policies = policies or DEFAULT_POLICIES

    def has_permission(self, role_name: str, permission: Permission) -> bool:
        """Check if a role name (string) is authorized for a permission.

        Args:
            role_name: Name of the role (e.g., 'admin', 'viewer').
            permission: Permission enum to check.

        Returns:
            True if the role has the permission, False otherwise.
        """
        try:
            role = Role(role_name)
        except ValueError:
            logger.warning("Attempted access with unknown role: %s", role_name)
            return False

        # Check all roles in hierarchy (includes inherited permissions)
        for r in ROLE_HIERARCHY.get(role, {role}):
            if permission in self._policies.get(r, set()):
                return True

        return False

    def authorize(self, role_name: str, permission: Permission) -> None:
        """Raises PermissionDeniedError if not authorized."""
        if not self.has_permission(role_name, permission):
            raise PermissionDeniedError(f"Role '{role_name}' lacks permission: {permission.name}")


# Global evaluator instance
RBAC = RBACEvaluator()
