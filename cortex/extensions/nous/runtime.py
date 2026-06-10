# [C5-REAL] Exergy-Maximized
"""NOUS Runtime - Intent-driven migration execution and dry-run engine

Reality Level: C5-REAL
"""

import logging

from cortex.engine import CortexEngine
from cortex.extensions.nous.dry_run import DryRunEngine
from cortex.extensions.nous.models import DryRunResult, NousAST
from cortex.extensions.nous.sql_synthesizer import SQLSynthesizer

logger = logging.getLogger(__name__)




class NousRuntime:
    def __init__(self, engine: CortexEngine):
        self.engine = engine

        # In real code, DryRunEngine could use self.engine internally
        self.dry_run_engine = DryRunEngine()



    async def dry_run(self, ast: NousAST) -> DryRunResult:
        """
        Executes a dry-run of the AST using the DryRunEngine.
        """

        logger.info("🛡️ [NOUS] Starting C5-REAL dry-run for %s", ast.metadata.version)

        operations = SQLSynthesizer.synthesize(ast)
        return await self.dry_run_engine.simulate(operations)

    async def execute(self, ast: NousAST):
        """
        Applies the compiled AST migration to the real engine.
        """

        logger.warning("⚠️ [NOUS] EXECUTING REAL MIGRATION: %s", ast.metadata.version)

        operations = SQLSynthesizer.synthesize(ast)

        async with self.engine.transaction() as tx:
            for op in operations:
                logger.debug("Executing: %s", op.sql_up)
                await tx.execute(op.sql_up)

            logger.info("✅ [NOUS] Migration %s applied.", ast.metadata.version)
