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

---

## 3. Defensa Epistemológica (Anti-Circularidad y Decaimiento)
Para evitar los dos mayores vectores de ataque contra los repositorios de conocimiento (la tautología y la obsolescencia), la EFT impone dos fronteras inviolables:

### 3.1. Guerra contra la Justificación Circular
Un agente malicioso o alucinado puede generar una `justification` del tipo *"Esto es cierto porque el modelo lo deduce"*. Para destruir este ataque de *Epistemic Circularity*, el `EFTVerificationGuardAdapter` analiza la estructura de la justificación. Se exige que la evidencia contenga al menos un anclaje verificable (marcadores físicos o matemáticos):
- Firma Criptográfica (`sha3_256:`, `ed25519:`)
- Demostración Formal (`z3_proof:`)
- Evidencia Empírica Medible (`metric:`, `test_hash:`)

### 3.2. Decaimiento Epistémico (Half-Life)
La Falsedad de la Verdad Permanente: En la ciencia estricta, ninguna verdad es eterna; solo ha sobrevivido a todos los intentos de falsación *hasta la fecha*. Por tanto, el estado `ACCEPTED` está prohibido si no incluye un `epistemic_half_life`.
- Un *KnowledgeObject* `ACCEPTED` caduca (transición automática a `UNVERIFIED` o `FALSIFIED`) cuando su half-life expira, forzando al sistema a re-evaluar la premisa ante un mundo mutante. Un repositorio sin decaimiento epistémico es un dogma, no una base de conocimiento.
