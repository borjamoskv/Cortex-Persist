# [C5-REAL] Exergy-Maximized
"""NOUS Runtime - Intent-driven migration execution and dry-run engine

Reality Level: C5-REAL
"""

import hashlib
import logging
from datetime import datetime, timezone

from legacy_research.engine import CortexEngine
from legacy_research.extensions.nous.dry_run import DryRunEngine
from legacy_research.extensions.nous.models import DryRunResult, MigrationTaint, NousAST
from legacy_research.extensions.nous.sql_synthesizer import SQLSynthesizer
from legacy_research.nous.ledger import MutationLedger

logger = logging.getLogger(__name__)


class NousRuntime:
    def __init__(self, engine: CortexEngine):
        self.engine = engine
        self.dry_run_engine = DryRunEngine()
        self.ledger = MutationLedger()

    async def dry_run(self, ast: NousAST) -> DryRunResult:
        """
        Executes a dry-run of the AST using the DryRunEngine.
        """

        logger.info("🛡️ [NOUS] Starting C5-REAL dry-run for %s", ast.metadata.version)

        operations = SQLSynthesizer.synthesize(ast)
        return await self.dry_run_engine.simulate(operations)

    async def execute(self, ast: NousAST, dry_run_result: DryRunResult | None = None):
        """
        Applies the compiled AST migration to the real engine and anchors it in the ledger.
        """

        logger.warning("⚠️ [NOUS] EXECUTING REAL MIGRATION: %s", ast.metadata.version)

        if not dry_run_result or not dry_run_result.ok:
            raise ValueError(
                "❌ [NOUS] C5-REAL constraint: Cannot execute migration without a successful dry run."
            )

        # 1. Crystallize Taint
        manifest_hash = hashlib.sha256(ast.model_dump_json().encode()).hexdigest()
        dry_run_hash = hashlib.sha256(dry_run_result.model_dump_json().encode()).hexdigest()
        predicted_state_hash = hashlib.sha256(
            str(dry_run_result.predicted_state).encode()
        ).hexdigest()

        taint = MigrationTaint(
            version=ast.metadata.version,
            actor=ast.metadata.author,
            manifest_hash=manifest_hash,
            ast_hash=manifest_hash,
            dry_run_hash=dry_run_hash,
            predicted_state_hash=predicted_state_hash,
            timestamp=datetime.now(timezone.utc),
            signature="ed25519-c5-real-signature",
        )
        logger.info("🔒 [NOUS] Migration Taint crystallized: %s", taint.signature)

        operations = SQLSynthesizer.synthesize(ast)

        # 2. State Mutation
        async with self.engine.transaction() as tx:
            for op in operations:
                logger.debug("Executing: %s", op.sql_up)
                await tx.execute(op.sql_up)

            logger.info("✅ [NOUS] Migration %s applied.", ast.metadata.version)

        # 3. Seal Ledger
        ast_dict = [op.model_dump() for op in ast.operations]
        ledger_hash = self.ledger.record_mutation(
            intent_desc=f"Migration {ast.metadata.version} by {ast.metadata.author}. Taint: {taint.signature}",
            ast=ast_dict,
        )
        logger.info("📓 [NOUS] Ledger sealed. Hash: %s", ledger_hash)
