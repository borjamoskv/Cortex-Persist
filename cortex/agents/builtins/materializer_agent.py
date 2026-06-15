# [C5-REAL] Exergy-Maximized
"""
CORTEX - Materializer Agent (JIT Fluid Intelligence).
Materializa las abstracciones ad-hoc (Axiom AX-046). Convierte "thermal noise"
e intenciones crudas en artefactos y ecosistemas persistidos (vía Keter) o 
en rutinas de ejecución dinámicas (SandboxJIT).
"""

import logging
from typing import Any

from cortex.agents.base import ReactiveTaskAgent
from cortex.engine.endocrine import ENDOCRINE, HormoneType
from cortex.engine.keter import KeterEngine
from cortex.engine.sandbox_jit import SandboxJIT
from cortex.engine.saga_protocol import build_core_write_path_saga, SagaContext
from cortex.utils.errors import CortexError
from cortex.verification.verifier import SovereignVerifier

logger = logging.getLogger(__name__)


class MaterializerAgent(ReactiveTaskAgent):
    """
    Agente fluido que sintetiza abstracciones ad-hoc en tiempo de ejecución.
    Implementa el pipeline de "JIT concept formation -> execute -> validate"
    con integración absoluta al SAGA Write-Path Protocol y Formal Verification Gate.
    """
    _SUPPORTED_OPS = frozenset({"materialize_intent", "jit_execute"})

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.keter = KeterEngine()
        self.sandbox = SandboxJIT()
        self.verifier = SovereignVerifier()
        self.saga_orchestrator = build_core_write_path_saga()

    async def _dispatch(self, op: str, payload: dict[str, Any]) -> Any:
        """Enruta la materialización según el tipo de abstracción (creacional vs. runtime)."""
        if op == "materialize_intent":
            intent = payload.get("intent", "")
            tenant_id = payload.get("tenant_id", "default")
            session_id = payload.get("session_id", "system")
            
            if not intent:
                ENDOCRINE.pulse(HormoneType.CORTISOL, 0.1, "Missing intent in Materializer")
                raise CortexError("Se requiere 'intent' (la abstracción a materializar) para materialize_intent")
            
            logger.info("🌌 [%s] Materializando abstracción (KETER IGNITE): %s", self.agent_id, intent)
            try:
                # 1. Keter Generates the Generative Proposal
                result = await self.keter.ignite(intent, thermal_audit=True, tenant_id=tenant_id, session_id=session_id)
                
                # 2. SAGA Protocol: Deterministic Validation and Persistence Boundary
                saga_ctx: SagaContext = {
                    "agent_id": self.agent_id,
                    "session_id": session_id,
                    "tenant_id": tenant_id,
                    "payload": result,
                }
                logger.info("🛡️ [%s] Invoking SAGA Write-Path Contract for Materialization", self.agent_id)
                await self.saga_orchestrator.execute_mutation(saga_ctx)
                
                # Axioma Ω-Dopamine: Recompensa por cristalización exitosa
                score = result.get("score_130_100", 0.0)
                if score >= 90.0:
                    ENDOCRINE.pulse(HormoneType.DOPAMINE, 0.2, f"High-fidelity abstraction crystallized ({score})")
                else:
                    ENDOCRINE.pulse(HormoneType.SEROTONIN, 0.1, "Homeostatic adaptation completed")
                
                return {
                    "status": "SAGA_COMMITTED",
                    "score": score,
                    "legion_audit": result.get("legion_audit", ""),
                    "fv_audit": result.get("fv_audit", ""),
                    "ledger_hash": saga_ctx.get("ledger_hash")
                }
            except Exception as e:
                ENDOCRINE.pulse(HormoneType.ADRENALINE, 0.5, "KETER/SAGA Collapse in Materializer")
                logger.error("🔥 [%s] Colapso de materialización (KETER/SAGA): %s", self.agent_id, e)
                raise CortexError(f"Fallo SAGA o forja de abstracción: {e}") from e
            
        elif op == "jit_execute":
            code_str = payload.get("code", "")
            if not code_str:
                ENDOCRINE.pulse(HormoneType.CORTISOL, 0.1, "Missing code in JIT Materializer")
                raise CortexError("Se requiere 'code' (el programa en miniatura) para jit_execute")
            
            logger.info("🛡️ [%s] Verificando Invariantes Z3 en abstracción ad-hoc", self.agent_id)
            try:
                # 1. Formal Verification Gate ANTES de inyectar en Sandbox
                verification_result = self.verifier.check(code_str)
                if not verification_result.is_valid:
                    ENDOCRINE.pulse(HormoneType.CORTISOL, 0.4, "Formal Verification Failure (JIT)")
                    raise CortexError(f"JIT Code violó invariantes de seguridad Z3: {verification_result.violations}")
                
                logger.info("⚡ [%s] Ejecutando abstracción ad-hoc JIT (SandboxJIT)", self.agent_id)
                context = payload.get("context", {})
                
                # 2. Ejecución dinámica (Memory Space Boundary)
                exec_result = self.sandbox.execute(code_str, context)
                
                # Purga de dunders para la sanidad de la memoria
                clean_locals = {k: str(v) for k, v in exec_result.items() if not k.startswith("__")}
                
                ENDOCRINE.pulse(HormoneType.NEURAL_GROWTH, 0.1, "Ad-hoc JIT abstraction executed safely")
                return {"status": "executed_clean", "locals": clean_locals}
                
            except Exception as e:
                ENDOCRINE.pulse(HormoneType.CORTISOL, 0.3, "SandboxJIT Violation")
                logger.error("🔥 [%s] Colapso de materialización JIT: %s", self.agent_id, e)
                raise CortexError(f"Violación de Sandbox JIT o error en runtime: {e}") from e
        
        raise NotImplementedError(f"Operación no soportada por el Materializador: {op}")

