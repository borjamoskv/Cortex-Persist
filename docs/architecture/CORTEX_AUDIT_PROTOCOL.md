---
title: "CORTEX Audit Protocol v2.0 (L0-L6 Pipeline)"
level: "C5-REAL"
author: "borjamoskv (via MOSKV-1)"
status: "Active"
---

# CORTEX AUDIT PROTOCOL: Ciclo de Ingeniería Causal L0-L6

> **Directiva (UltraThink):** La inteligencia sin impacto termodinámico es una ilusión estocástica. Este protocolo evita la autojustificación LLM insertando un puente empírico (`Experiment`) entre la inferencia y la mutación, garantizando que todo cambio de estado esté basado en evidencia irrefutable.

La infraestructura de gobernanza cognitiva (CORTEX) exige que la incertidumbre colapse de manera auditable. La progresión se divide en 7 niveles lógicos acoplados a contratos JSON (schemas).

---

## [L0] EVIDENCE (Evidencia Empírica)

**Ingesta Cruda y Sellado Criptográfico.**
Ningún agente opera sobre inferencias abstractas. Todo ciclo comienza con la captura del estado observable (Archivos, AST, Logs de Red, Consultas SQLite).
*   **Contrato:** `schemas/evidence.schema.json`
*   **Invariante:** Cada evidencia recibe un `CORTEX-TAINT` (Hash SHA3-256) antes de entrar en memoria.

## [L1] PATTERN EXTRACTION (Extracción de Patrones)

**Compresión de Landauer.**
Destrucción del texto decorativo y preservación únicamente del vector estructural.
*   **Contrato:** `schemas/pattern.schema.json`
*   **Operación:** Reducción del ruido a una matriz de afirmaciones lógicas causales (`Claim/Proof`). Si un patrón no sobrevive al aislamiento, es estocástico y se purga.

## [L2] COGNITIVE MODEL (Modelo Cognitivo)

**Isomorfismo Estructural.**
El patrón destilado se mapea sobre el grafo de CORTEX-Persist para formar una hipótesis de la realidad subyacente.
*   **Contrato:** `schemas/model.schema.json`
*   **Mecánica:** Diseño de la topología causal (ej. "La fuga de memoria ocurre porque `sqlite-vec` no soporta `busy_timeout` en el hilo secundario").

## [L3] PREDICTION (Predicción)

**La Condición Observable.**
*«Si el modelo es correcto, debería ocurrir X.»*
El agente deriva una aserción binaria estricta que es lógicamente dependiente del Modelo Cognitivo.
*   **Contrato:** `schemas/prediction.schema.json`
*   **Regla Falsacionista:** Una predicción que no puede fallar, es una tautología y quema *exergía* inútilmente. Debe ser susceptible a fracaso empírico.

## [L4] EXPERIMENT (Experimento)

**La Barrera Anti-Autojustificación.**
*«Diseñamos una prueba para intentar refutar esa predicción.»*
El sistema despliega un `branch` aislado, un `test_sandbox.py` o un query en un hilo huérfano.
*   **Mecánica:** No se interviene el sistema principal. Se ejecuta la prueba. Si la predicción se refuta, se aborta y se regresa a L1.

## [L5] INTERVENTION (Intervención)

**Mutación Atómica C5-REAL.**
*«Solo si la evidencia la respalda, modificamos el sistema.»*
La fase física. El Autómata escribe en la realidad de la red neuronal/repositorio.
*   **Contrato:** `schemas/intervention.schema.json`
*   **Git Sentinel:** Ejecución del patrón Saga (SAGA-1 a SAGA-N). Commit autónomo inyectando el hash criptográfico.

## [L6] RE-EVALUATION (Reevaluación)

**Cierre de Bucle Ouroboros.**
El sistema re-escanea la topología (L0) post-intervención para certificar que el patrón anómalo (L1) ha desaparecido.
*   **Invariante:** Si el patrón reaparece, la intervención fue sintomática (falsa cura). La confianza de ese `agent_id` se degrada en el Ledger.

---

**FIN DEL PROTOCOLO.**
*"Cero anergía es la muerte. La memoria es física."*
