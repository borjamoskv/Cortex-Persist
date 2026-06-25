"""
Semantic CRDT Orchestrator.

Bridges the deterministic Rust `cortex_rs.SemanticState` with the async `EnterpriseAuditLedger`.
Catches BufferError exceptions from the zero-copy CRDT arrays, orchestrating a cryptographic
compaction sequence to the Ledger to maintain mathematical provenance before resuming operations.
"""

import logging
from typing import Optional

import cortex_rs
from legacy_research.audit.ledger import EnterpriseAuditLedger
from legacy_research.auth.enterprise_identity import SovereignIdentity, TenantRBAC

logger = logging.getLogger("cortex.engine.logic.semantic_crdt")

class SemanticOrchestrator:
    """
    Orchestrates operations on a SemanticState CRDT, ensuring cryptographic provenance
    is maintained via the EnterpriseAuditLedger when the state undergoes compaction.
    """

    def __init__(self, ledger: EnterpriseAuditLedger, identity: SovereignIdentity, initial_state: Optional[cortex_rs.SemanticState] = None):
        self.ledger = ledger
        self.identity = identity
        self.state = initial_state if initial_state else cortex_rs.SemanticState()

    async def add_active_support(self, id_str: str) -> None:
        try:
            self.state.add_active_support(id_str)
        except BufferError:
            logger.info("BufferError: active_supports full. Orchestrating compaction.")
            await self._compact_active_supports()
            # Retry after explicit ledger compaction
            self.state.add_active_support(id_str)

    async def add_discard_evidence(self, id_str: str) -> None:
        try:
            self.state.add_discard_evidence(id_str)
        except BufferError:
            logger.info("BufferError: discard_evidence full. Orchestrating compaction.")
            await self._compact_discard_evidence()
            self.state.add_discard_evidence(id_str)

    async def add_dependency(self, id_str: str) -> None:
        try:
            self.state.add_dependency(id_str)
        except BufferError:
            logger.info("BufferError: dependencies full. Orchestrating compaction.")
            await self._compact_dependencies()
            self.state.add_dependency(id_str)

    async def merge(self, other_state: cortex_rs.SemanticState) -> None:
        """
        Merges another SemanticState into this one. If an overflow occurs,
        compacts all buffers that are full to ensure the merge can proceed.
        """
        while True:
            try:
                self.state.merge(other_state)
                break  # Merge succeeded without overflow
            except BufferError:
                logger.warning("BufferError during merge. Triggering safety compactions.")
                # We compact everything that has data to guarantee enough space for the merge
                if self.state.active_supports:
                    await self._compact_active_supports()
                if self.state.discard_evidence:
                    await self._compact_discard_evidence()
                if self.state.dependencies:
                    await self._compact_dependencies()
                # Retry merge in the next loop iteration

    async def _compact_active_supports(self) -> None:
        if not TenantRBAC.validate_action(self.identity, "crdt:compact"):
            raise PermissionError(f"Identity {self.identity.actor_id} lacks 'crdt:compact' scope for Tenant {self.identity.tenant_id}")

        items = self.state.active_supports
        resource = f"compact:active_supports:[{','.join(items)}]"
        
        # Step 1: Securely log the items being compacted to the Ledger to get a cryptographic proof
        audit_id = await self.ledger.log_action(
            tenant_id=self.identity.tenant_id,
            actor_role=self.identity.role,
            actor_id=self.identity.actor_id,
            action="CRDT_COMPACT",
            resource=resource,
            status="SUCCESS"
        )
        
        # Step 2: Push the cryptographic proof (audit_id) to the Rust CRDT to maintain provenance
        self.state.compact_active_supports(audit_id)

    async def _compact_discard_evidence(self) -> None:
        if not TenantRBAC.validate_action(self.identity, "crdt:compact"):
            raise PermissionError("Permission denied: crdt:compact")

        items = self.state.discard_evidence
        resource = f"compact:discard_evidence:[{','.join(items)}]"
        
        audit_id = await self.ledger.log_action(
            tenant_id=self.identity.tenant_id,
            actor_role=self.identity.role,
            actor_id=self.identity.actor_id,
            action="CRDT_COMPACT",
            resource=resource,
            status="SUCCESS"
        )
        self.state.compact_discard_evidence(audit_id)

    async def _compact_dependencies(self) -> None:
        if not TenantRBAC.validate_action(self.identity, "crdt:compact"):
            raise PermissionError("Permission denied: crdt:compact")

        items = self.state.dependencies
        resource = f"compact:dependencies:[{','.join(items)}]"
        
        audit_id = await self.ledger.log_action(
            tenant_id=self.identity.tenant_id,
            actor_role=self.identity.role,
            actor_id=self.identity.actor_id,
            action="CRDT_COMPACT",
            resource=resource,
            status="SUCCESS"
        )
        self.state.compact_dependencies(audit_id)
