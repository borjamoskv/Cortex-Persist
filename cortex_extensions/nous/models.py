# [C5-REAL] Exergy-Maximized
"""NOUS Models - Data Contracts for CORTEX/NOUS Migrator

Reality Level: C5-REAL
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class MigrationOperation(BaseModel):
    op: Literal[
        "create_table",
        "alter_table",
        "drop_table",
        "create_index",
        "drop_index",
        "add_column",
        "drop_column",
        "alter_column",
        "add_constraint",
        "drop_constraint",
        "create_function",
        "drop_function",
        "create_trigger",
        "drop_trigger",
        "create_view",
        "drop_view",
        "grant",
        "revoke",
        "raw_sql",
    ]
    table: str | None = None
    sql_up: str  # Forward migration
    sql_down: str  # Rollback (auto-generated or explicit)
    constraints: list[str] = Field(default_factory=list)  # "no_lock", "reversible", etc.


class GuardResult(BaseModel):
    guard: str
    passed: bool
    details: str | None = None
    severity: Literal["error", "warning", "info"] = "error"


class DryRunResult(BaseModel):
    ok: bool
    plan: list[MigrationOperation]
    guards: dict[str, GuardResult]
    predicted_state: dict  # schema hash, row counts, constraint status
    warnings: list[str] = Field(default_factory=list)
    estimated_lock_time_ms: int = 0
    estimated_data_loss_risk: Literal["none", "low", "medium", "high"] = "none"


class MigrationTaint(BaseModel):
    version: str = "0.1"
    actor: str
    manifest_hash: str  # SHA256 of .nous source
    ast_hash: str  # SHA256 of compiled NousAST
    dry_run_hash: str  # SHA256 of DryRunResult
    predicted_state_hash: str
    timestamp: datetime
    signature: str  # Ed25519(actor + all_above)


# AST Models
class NousInvariant(BaseModel):
    name: str
    condition: str
    action: str = "halt"


class NousOperation(BaseModel):
    type: str  # e.g., "create_table", "add_column", "drop_table"
    target: str
    sql: str
    rollback_sql: str | None = None


class NousMetadata(BaseModel):
    version: str
    author: str
    description: str
    requires_lock: bool = True


class NousAST(BaseModel):
    metadata: NousMetadata
    ensures: list[str]
    operations: list[NousOperation]
    invariants: list[NousInvariant]
