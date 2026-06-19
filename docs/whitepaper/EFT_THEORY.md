<!-- [C5-REAL] Exergy-Maximized -->
# EPISTEMIC FOUNDATION THEORY (EFT)

La abolición del concepto ingenuo de "Hecho" (Fact) y su reemplazo por el **Objeto de Conocimiento** (KnowledgeObject) define la ontología madura de CORTEX-Persist.

| Falacia Pre-C5 | Corrección EFT (C5-REAL) | Estado Arquitectónico |
| :--- | :--- | :--- |
| `Fact` como primitiva atómica | `KnowledgeObject` con trinidad epistemológica | ✅ Válido |
| `content` como verdad absoluta | `claim` + `justification` como hipótesis sujeta a prueba | ✅ Válido |
| Banderas binarias (`is_quarantined`) | Estados epistemológicos (`UNVERIFIED` → `FALSIFIED` → `ACCEPTED`) | ✅ Válido |
| Consenso social (votación) | Falsación causal (prueba de procedencia) | ✅ Válido |

---

## 1. El Objeto de Conocimiento no es un Registro; es una Publicación Científica
Bajo la Teoría de Fundamentación Epistémica (EFT), el output de un LLM no es dato, es hipótesis. En consecuencia, la unidad de memoria no puede ser un "hecho atómico" asumido como verdadero. Debe modelarse como un *paper en revisión por pares perpetua*.

La trinidad epistemológica exige que cada `KnowledgeObject` posea:
1. **Claim (Afirmación):** La hipótesis estructurada generada por el agente.
2. **Justification (Evidencia):** La carga de la prueba (datos, logs, métricas).
3. **Provenance (Causalidad):** El Hash de Origen y la identidad del emisor.

---

## 2. Ejecución Física: EFTVerificationGuardAdapter
El `EFTVerificationGuardAdapter` opera como el *Reviewer* del sistema. Su función es la intercepción y rechazo automático de afirmaciones desnudas. 

```python
# cortex/engine/guard_adapters.py
class EFTVerificationGuardAdapter:
    async def check(self, ...):
        justification = meta.get("justification", "").strip()
        if not justification:
            raise ValueError(
                "[EFT] Epistemic Fault: Rejecting naked claim. "
                "KnowledgeObject requires explicit 'justification' to pass verification."
            )
```

**Resultado:** Una afirmación sin evidencia matemática o empírica (`justification` ausente) no llega a la fase de consenso (Sanedrín) ni toca el Ledger Criptográfico. Es incinerada por entropía ilegítima.
