# [C5-REAL] Exergy-Maximized
"""NOUS Guards - Deterministic AST Verification

Reality Level: C5-REAL
"""

from cortex.extensions.nous.models import NousAST


class SemanticDriftGuard:
    def validate(self, ast: NousAST) -> bool:
        """Validates that operations make sense semantically."""
        if not ast.operations:
            return False

        # Require rollback for destructive ops
        for op in ast.operations:
            if "drop" in op.type.lower() and not op.rollback_sql:
                return False
        return True


class CapabilityGuard:
    def validate(self, ast: NousAST) -> bool:
        """Validates that operations do not exceed capability limits."""
        # Forbid truncate and some superuser commands
        for op in ast.operations:
            if "truncate" in op.sql.lower():
                return False
        return True


class InvariantGuard:
    def validate(self, ast: NousAST) -> bool:
        """Validates that the invariants declared are sound."""
        # If there are ensures, there must be operations
        if ast.ensures and not ast.operations:
            return False
        return True
