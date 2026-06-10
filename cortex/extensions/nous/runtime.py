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

from cortex.extensions.nous.guards import CapabilityGuard, InvariantGuard, SemanticDriftGuard


class NousRuntime:
    def __init__(self, engine: CortexEngine):
        self.engine = engine
        self.guards = [
            SemanticDriftGuard(),
            CapabilityGuard(),
            InvariantGuard(),
        ]
        # In real code, DryRunEngine could use self.engine internally
        self.dry_run_engine = DryRunEngine()

    async def _run_guards(self, ast: NousAST):
        for guard in self.guards:
            if not guard.validate(ast):
                raise ValueError(
                    f"Guard {guard.__class__.__name__} failed for migration: {ast.metadata.version}"
                )

    async def dry_run(self, ast: NousAST) -> DryRunResult:
        """
        Executes a dry-run of the AST using the DryRunEngine.
        """
        await self._run_guards(ast)
        logger.info("🛡️ [NOUS] Starting C5-REAL dry-run for %s", ast.metadata.version)

        operations = SQLSynthesizer.synthesize(ast)
        return await self.dry_run_engine.simulate(operations)

    async def execute(self, ast: NousAST):
        """
        Applies the compiled AST migration to the real engine.
        """
        await self._run_guards(ast)
        logger.warning("⚠️ [NOUS] EXECUTING REAL MIGRATION: %s", ast.metadata.version)

        operations = SQLSynthesizer.synthesize(ast)

        async with self.engine.transaction() as tx:
            for op in operations:
                logger.debug("Executing: %s", op.sql_up)
                await tx.execute(op.sql_up)

            logger.info("✅ [NOUS] Migration %s applied.", ast.metadata.version)
