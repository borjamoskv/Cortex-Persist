import asyncio
import logging
from typing import Any

import numpy as np

try:
    from cortex.extensions.agents.factory import create_agent  # type: ignore[import-not-found]
except ImportError:

    async def create_agent(*args: Any, **kwargs: Any) -> Any:  # type: ignore[misc]
        """Stub: agents.factory removed during extensions refactor."""
        raise NotImplementedError("cortex.extensions.agents.factory was removed")


from cortex.extensions.swarm.infinite_minds import InfiniteMindsManager

try:
    from cortex.memory.hdc.algebra import DEFAULT_DIM, bundle
    from cortex.memory.hdc.codec import HDCEncoder
    from cortex.memory.hdc.item_memory import ItemMemory
except ImportError:
    pass

logger = logging.getLogger("cortex.extensions.swarm.deep_think")


class DeepThinkOrchestrator:
    """
    DEEP THINK Protocol (11-Agent Mesh).

    Inyecta simultáneamente el contexto Waveform 4D (Spatial 8K + Temporal + Proof + Intention)
    a los 10 agentes rasos. Cada uno devuelve un vector HDC de decisión.
    El 11º Astro (MARADONA_10_OMEGA) colapsa la función de onda de los 10 vectores.
    """

    def __init__(self, engine: Any, minds_manager: InfiniteMindsManager):
        self.engine = engine
        self.minds_manager = minds_manager
        self.agents_ids = [
            "julen_guerrero_omega",
            "maldini_arch_omega",
            "zubizarreta_redteam_omega",
            "dunga_chaos_omega",
            "romario_data_omega",
            "baggio_sync_omega",
            "stoichkov_finance_omega",
            "bebeto_yield_omega",
            "zubi_bridge_omega",
            "valderrama_vision_omega",
        ]

        # Local HDC Codec for orchestrator-level encoding if needed
        self.mem = ItemMemory(dim=DEFAULT_DIM, maxsize=5000)
        self.encoder = HDCEncoder(self.mem)

    async def pulse(self, waveform_context: str, project: str = "SYSTEM") -> str:
        """
        Inicia un ciclo de Deep Siege. Contexto inyectado a los 11.
        """
        logger.info("🌊 [DEEP THINK] Iniciando inyección de onda a los 10 Astros.")

        # 1. Inyección 4D Simultánea con Válvula Termodinámica (Semaphore 3)
        sem = asyncio.Semaphore(3)
        vector_perspectives = await self._gather_vector_perspectives(waveform_context, project, sem)

        hvs = [p["hv"] for p in vector_perspectives if p["hv"] is not None]
        text_context = "\n".join([f"- {p['agent_id']}: {p['text']}" for p in vector_perspectives])

        # 2. Tribunal Asíncrono - Diagnostics
        diagnostics = await self.minds_manager.convergence_pulse()

        # 3. Colapso de Función (El 11º Astro)
        logger.info("⚡ [DEEP THINK] MARADONA_10_OMEGA ejecutando colapso de función.")
        final_truth = await self._maradona_synthesis(hvs, text_context, diagnostics, project)

        return final_truth

    async def _gather_vector_perspectives(
        self, context: str, project: str, sem: asyncio.Semaphore
    ) -> list[dict[str, Any]]:
        """Recopila razonamientos en crudo y sus firmas HDC."""
        tasks = [
            self._get_vector_reasoning(agent_id, context, project, sem)
            for agent_id in self.agents_ids
        ]
        return list(await asyncio.gather(*tasks))

    async def _get_vector_reasoning(
        self, agent_id: str, context: str, project: str, sem: asyncio.Semaphore
    ) -> dict[str, Any]:
        """Invoca el agente, extrae su texto y lo comprime a HDC."""
        bus = await self.engine.get_bus()
        agent = await create_agent(agent_id, self.engine.memory.l3, bus)

        if not agent:
            return {"agent_id": agent_id, "hv": None, "text": "Failed to manifest."}

        # Override temporal knowledge to force immediate context evaluation
        prompt = f"WAVEFORM CONTEXT:\n{context}\n\nEVALUATE AND CONVERGE:"

        try:
            async with sem:
                # Not all agents might have deliberate taking prompt, but we assume deliberate()
                # or custom interact(). We'll wrap deliberate or send a cortex_prompt directly.
                # BaseCortexAgent generic usage:
                if hasattr(agent, "router"):
                    from cortex.extensions.llm.router import CortexPrompt, IntentProfile

                    cortex_prompt = CortexPrompt(
                        system_instruction=f"{agent.persona.vision}\n{';'.join(agent.persona.axioms)}",
                        working_memory=[{"role": "user", "content": prompt}],
                        intent=IntentProfile.REASONING,
                        project=project,
                    )
                    res = await agent.router.execute_resilient(cortex_prompt)
                    text_response = res.unwrap() if res.is_ok() else "Error in deliberation"
                else:
                    text_response = await agent.deliberate()

            # Encode response to HDC vector and Bind Author (Vectorial Entanglement)
            from cortex.memory.hdc.algebra import bind

            text_hv = self.encoder.encode_text(text_response[:2000])  # cap for speed
            agent_id_hv = self.encoder.encode_text(agent_id)
            hv = bind(agent_id_hv, text_hv)

        except Exception as e:  # noqa: BLE001 — intentional isolation for agent reasoning error
            logger.error("Agent %s failed in deep think: %s", agent_id, e)
            hv = self.encoder.encode_text("error")
            text_response = "Error."

        return {"agent_id": agent_id, "hv": hv, "text": text_response}

    async def _maradona_synthesis(
        self, hvs: list[np.ndarray], text_context: str, diagnostics: Any, project: str
    ) -> str:
        """Maradona ejecuta el bundle HDC y emite la decisión absoluta."""
        bus = await self.engine.get_bus()
        maradona = await create_agent("maradona_10_omega", self.engine.memory.l3, bus)

        if not maradona:
            raise RuntimeError("Maradona failed to manifest for Deep Think synthesis.")

        # Realizar el colapso matemático HDC (Umbral por defecto en majority algebra)
        if len(hvs) > 1:
            collapsed_hv = bundle(*hvs)
        elif len(hvs) == 1:
            collapsed_hv = hvs[0]
        else:
            collapsed_hv = self.encoder.encode_text("void")

        import hashlib

        hv_signature = hashlib.sha256(collapsed_hv.tobytes()).hexdigest()[:16]

        # Resonancia Bizantina (Consensus Calculation)
        from cortex.memory.hdc.algebra import similarity  # type: ignore[reportAttributeAccessIssue]

        sims = []
        for i in range(len(hvs)):
            for j in range(i + 1, len(hvs)):
                sims.append(similarity(hvs[i], hvs[j]))

        avg_sim = float(np.mean(sims)) if sims else 1.0

        byzantine_alarm = ""
        if avg_sim < 0.4:
            byzantine_alarm = f"\n⚠️ **BYZANTINE ALARM (Alta Entropía)**: La resonancia del enjambre es {avg_sim:.2f}. El enjambre está fracturado. FORCE ABSOLUTE TRUTH OVERRIDE.\n"

        enhanced_context = (
            f"DIAGNOSTICS: {diagnostics}\n"
            f"VECTOR SUPERPOSITION (HDC): 0x{hv_signature}\n"
            f"SWARM RESONANCE: {avg_sim:.2f}\n"
            f"{byzantine_alarm}"
            f"SWARM PERSPECTIVES:\n{text_context}\n"
        )

        if hasattr(maradona, "collapse_waveform"):
            result = await maradona.collapse_waveform(collapsed_hv, hv_signature, enhanced_context)
            final_decision = result["decision"]
        else:
            final_decision = await maradona.synthesize_legion_reasoning(enhanced_context)
            if isinstance(final_decision, dict):
                final_decision = final_decision.get("decision", str(final_decision))

        await self.engine.store(
            project=project,
            content=final_decision,
            fact_type="bridge",
            confidence="C5",
            source="maradona:deep-think",
            meta={
                "sub_type": "deep_think_collapse",
                "signature": hv_signature,
                "dimension": DEFAULT_DIM,
                "diagnostics": str(diagnostics),
            },
        )
        return final_decision
