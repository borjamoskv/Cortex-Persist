# THERMODYNAMIC-ENFORCEMENT.md

## 0. Regla Madre

Ningún axioma existe si no puede producir al menos una de estas consecuencias:
- `raise`
- `abort`
- `degrade_trust`
- `quarantine`
- `deny_write`
- `force_observation_cycle`

Si no hace una de esas seis cosas, es decoración.

---

## 1. Exergía Medible (`cortex/shannon/exergy.py`)

No basta con decir "medimos trabajo útil". Exergía significa que cada token consumido es pesado contra la reducción de incertidumbre que produce, mitigado por el riesgo irreversible de la acción.
- **Riesgo:** Clasificado como `read_only`, `memory_write`, `file_write`, `schema_mutation`, `destructive`.
- **Contrato Mecánico:** Todo agente estocástico que proponga un cambio de estado debe justificar su `ExergyResult`.
- **Efecto:** Si `ExergyResult.below_threshold == True`, se levanta `ThermodynamicWasteError` abortando el flujo de ejecución.

---

## 2. Decorative Mode (`cortex/guards/thermodynamic.py`)

El hipervisor detecta cuando un proceso o agente entra en estado de paseo y "generación ornamental":
- `tool_fails_without_new_hypothesis >= 3`
- `file_reads_without_ast_delta >= 5`
- `context_expansion_rate > uncertainty_reduction_rate`

**Efecto de entrar en modo `DECORATIVE`:**
- Solo lectura (0 writes concedidos).
- Se fuerza al sistema a volver al ciclo `[OBSERVE]`.
- Requiere nueva hipótesis explícita y disminución de contexto antes de reactivarse en modo `ACTIVE`.

---

## 3. Suntsitu Acotado (`cortex/immune/quarantine.py`)

Autonomía absoluta destructiva es inaceptable.
- Antes de una purga física, se calcula el **Blast Radius** (dependencias AST, imports cruzados, pruebas en el ledger).
- Si el módulo es crítico (ej. `criticality_score > 0.4`), no se demuele directamente, pasa a `QUARANTINE`.
- Purgas destructivas sin snapshots (`has_snapshot == False`) quedan tajantemente restringidas (`requires_snapshot = True`).
- **Efecto:** Prevención de demolición kamikaze autónoma y obligatoriedad de rollback precalculado.

---

## 4. Semantic Tombstones y Contaminación Causal (`cortex/engine/causality.py`)

El CORTEX Ledger no es ontología pura, es registro de decisiones. Cuando una hipótesis que se consideraba válida resulta ser errónea, la refutación **se propaga**.
- La confianza base decae (`decay` asintótico por profundidad en el DAG causal).
- El flag `tainted=True` enreda los nodos descendentes de la hipótesis refutada.
- **Efecto:** El sistema se aísla a fallar por "cascada de ruido", ya que se castiga y veta el uso de contexto que emane de nodos refutados para operaciones destructivas upstream.
