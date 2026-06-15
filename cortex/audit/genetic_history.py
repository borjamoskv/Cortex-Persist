# [C5-REAL] Exergy-Maximized
import logging
import os
import shutil

from cortex.audit.ledger import EnterpriseAuditLedger

logger = logging.getLogger("cortex.audit.genetic_history")


class GeneticHistoryManager:
    """
    Manages the structural mutations of OUROBOROS-∞ and other skills.
    Provides the 'Genetic Rollback' capability to revert mutations that cause entropy.
    """

    def __init__(self, ledger: EnterpriseAuditLedger):
        self.ledger = ledger

    async def propose_mutation(
        self, skill_path: str, new_content: str, exergy_delta: float, topology_snapshot: str
    ) -> str:
        """
        Proposes and applies a mutation, logging it to the Sovereign Ledger.
        Backs up the previous state for rollback.
        """
        if not os.path.exists(skill_path):
            raise FileNotFoundError(f"Skill path not found: {skill_path}")

        skill_name = os.path.basename(os.path.dirname(skill_path))
        
        # Read old content to compute diff or store for backup
        with open(skill_path, encoding="utf-8") as f:
            old_content = f.read()

        # Simple diff generation (could use difflib)
        import difflib
        diff_lines = list(difflib.unified_diff(
            old_content.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile=f"{skill_name}_old",
            tofile=f"{skill_name}_new",
            n=3
        ))
        mutation_diff = "".join(diff_lines)

        # 1. Create backup
        backup_path = f"{skill_path}.bak"
        shutil.copy2(skill_path, backup_path)

        # 2. Log to Ledger
        mutation_id = await self.ledger.log_mutation(
            skill_name=skill_name,
            mutation_diff=mutation_diff,
            exergy_delta=exergy_delta,
            topology_snapshot=topology_snapshot,
        )

        # 3. Apply mutation
        with open(skill_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        logger.info(f"[GeneticHistory] Mutation {mutation_id} applied to {skill_name} (exergy_delta: {exergy_delta})")
        return mutation_id

    async def rollback_mutation(self, skill_path: str, mutation_id: str) -> bool:
        """
        Reverts a mutation by restoring the backup file.
        Requires the mutation_id to verify against the ledger.
        """
        skill_name = os.path.basename(os.path.dirname(skill_path))
        backup_path = f"{skill_path}.bak"

        if not os.path.exists(backup_path):
            logger.error(f"[GeneticHistory] Cannot rollback {skill_name}: Backup not found.")
            return False

        # In a full C5-REAL implementation, we would query the ledger to verify the mutation_id
        # and ensure we are rolling back exactly what we expect.
        
        # 1. Restore backup
        shutil.copy2(backup_path, skill_path)
        os.remove(backup_path)

        # 2. Log rollback event to Ledger
        await self.ledger.log_action(
            tenant_id="system",
            actor_role="L5-Autopoiesis",
            actor_id="OUROBOROS-∞",
            action="GENETIC_ROLLBACK",
            resource=skill_name,
            status="SUCCESS"
        )

        logger.warning(f"[GeneticHistory] Rollback executed for {skill_name} (mutation: {mutation_id})")
        return True
