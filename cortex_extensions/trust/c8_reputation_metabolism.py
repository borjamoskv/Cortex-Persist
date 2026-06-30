# [C5-REAL] Exergy-Maximized
"""C8 Reputation Metabolism.

Motor metabólico soberano para forjar y mutar BeliefObjects de reputación.
Aplica inferencia de exergía a las interacciones y persiste las mutaciones
inmutablemente en el Ledger para cristalizar la evolución causal de la confianza.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from cortex_extensions.hypervisor.belief_object import (
    BeliefConfidence,
    BeliefObject,
    ProvenanceChain,
    ProvenanceEntry,
)
from cortex_extensions.trust.bayesian import BayesianTrustUpdater, Signal

if TYPE_CHECKING:
    from cortex.engine import CortexEngine

logger = logging.getLogger("cortex_extensions.trust.c8_reputation_metabolism")


class ReputationMetabolism:
    """Metabolismo dinámico de Reputación C8.
    
    Gestiona la evolución térmica de la confianza hacia agentes o nodos empíricos,
    persistiendo invariablemente cada mutación como un BeliefObject en el CortexEngine.
    """

    __slots__ = ("_engine", "_updater")

    def __init__(self, engine: CortexEngine) -> None:
        self._engine = engine
        self._updater = BayesianTrustUpdater(engine)

    async def register_interaction(
        self,
        entity_id: str,
        interaction_type: str,
        signal: Signal | str,
        project: str,
        tenant_id: str = "default",
        source_id: str = "c8_metabolism",
    ) -> BeliefObject:
        """Cristaliza una nueva interacción, muta la reputación y persiste en Ledger.
        
        Si la entidad no tiene un BeliefObject de reputación, se crea (C2 base).
        Si ya lo tiene, se actualiza la confianza usando el modelo bayesiano y se muta.
        
        Args:
            entity_id: El ID de la entidad observada (ej. agente, usuario, dominio).
            interaction_type: Clasificación exérgica (ej. "payload_delivery", "fraud_attempt").
            signal: Señal bayesiana de la evidencia (CONFIRM, CONTRADICT, etc).
            project: Espacio topológico.
            tenant_id: Aislamiento multitenant.
            source_id: Origen de la métrica (sensor o agente).
            
        Returns:
            El BeliefObject de reputación mutado.
        """
        sig = Signal(signal) if isinstance(signal, str) else signal
        
        # 1. Recuperar el estado empírico (BeliefObject de reputación)
        query = f"project:{project} type:reputation entity:{entity_id}"
        facts = await self._engine.recall(query=query, project=project, limit=1)
        
        from cortex_extensions.hypervisor.belief_object import _now_iso

        if not facts:
            # Forja Cero-Entropía (Génesis de Reputación)
            prov_entry = ProvenanceEntry(
                source_type="metabolism",
                source_id=source_id,
                model="none",
                timestamp=_now_iso(),
                action="genesis",
            )
            belief = BeliefObject(
                content=f"Reputación base para entidad {entity_id}",
                project=project,
                tenant_id=tenant_id,
                confidence=BeliefConfidence.C3_PROBABLE,  # Neutral prior
                provenance=ProvenanceChain(entries=(prov_entry,))
            )
            old_conf = "C3"
            new_conf = "C3"
            fact_id = None
        else:
            # Reconstrucción del BeliefObject
            fact = facts[0]
            meta = fact.meta if isinstance(fact.meta, dict) else {}
            belief_data = meta.get("belief_object")
            if belief_data and isinstance(belief_data, dict):
                belief = BeliefObject.from_dict(belief_data)
            else:
                conf_val = str(fact.confidence)
                valid_confs = {c.value for c in BeliefConfidence}
                belief = BeliefObject(
                    content=fact.content,
                    project=project,
                    tenant_id=tenant_id,
                    confidence=BeliefConfidence(conf_val) if conf_val in valid_confs else BeliefConfidence.C3_PROBABLE,
                )
            fact_id = fact.id
            old_conf = belief.confidence.value
            
            # Ejecutar mutación bayesiana si existe fact_id
            if fact_id is not None:
                update_result = await self._updater.update(fact_id, sig, tenant_id=tenant_id)
                new_conf = update_result.new_confidence
                from dataclasses import replace
                new_prov = belief.provenance.extend(
                    ProvenanceEntry(
                        source_type="metabolism",
                        source_id=source_id,
                        model="none",
                        timestamp=_now_iso(),
                        action="revised"
                    )
                )
                belief = replace(
                    belief,
                    confidence=BeliefConfidence(new_conf),
                    provenance=new_prov
                )
            else:
                new_conf = old_conf

        # 2. Persistir mutación en Ledger de forma inmutable
        meta_payload = {
            "entity_id": entity_id,
            "interaction_type": interaction_type,
            "signal": sig.value,
            "belief_object": belief.to_dict(),
            "status": belief.status.value,
        }
        
        # Si era nuevo, lo guardamos. Si ya existía, el BayesianTrustUpdater actualizó el fact nativo,
        # pero inyectamos un evento de mutación explícito en el Ledger para observabilidad C8.
        await self._engine.store(
            content=f"Mutación de reputación [{entity_id}]: {old_conf} -> {new_conf} via {interaction_type}",
            fact_type="reputation_mutation",
            project=project,
            source=source_id,
            meta=meta_payload,
            confidence=new_conf,
        )
        
        logger.info(
            "C8 Metabolism [%s]: %s -> %s (Signal: %s)",
            entity_id, old_conf, new_conf, sig.value
        )
        
        return belief
