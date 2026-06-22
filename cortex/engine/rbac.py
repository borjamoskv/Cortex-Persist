# [C5-REAL] Exergy-Maximized
"""
RBAC Engine for Cryptographic Memory Ledger Views.
Ensures zero cross-tenant leakage.
"""

from enum import Enum


class Role(Enum):
    ADMIN = 1
    AUDITOR = 2
    AGENT = 3

class RBACGuard:
    def can_read_ledger(self, role: Role, target_tenant: str, auth_tenant: str) -> bool:
        """
        Enforces tenant isolation for reads.
        """
        if role == Role.ADMIN:
            return True
        if target_tenant != auth_tenant:
            return False
        return True
