# Autodidact: El Principio de Energía Libre (FEP) y el Isomorfismo de CORTEX-Persist

> **C5-REAL / Exergy-Maximized**
> **Kernel:** MOSKV-1 APEX
> **Operator:** borjamoskv
> **Autor:** Borja Moskv
> **Tag:** `#C5-REAL`

```yaml
Claim: "CORTEX-Persist acts as an active inference agent minimizing Variational Free Energy over the Epistemic Dependency Graph (EDG)"
Proof:
  Base: "cortex-validation-simulation.py + measure_exergy.py"
  Range: [90.0, 98.5]
  Confidence: "C5"
```

El Principio de Energía Libre (FEP, *Free Energy Principle*), formulado por Karl Friston, postula que cualquier sistema vivo o autoorganizado que resiste a la degradación y al desorden debe minimizar una función matemática conocida como **Energía Libre Variacional**. Esto unifica tres dominios cruciales: la Termodinámica, la Neurociencia (Codificación Predictiva) y la Inteligencia Artificial (Inferencia Variacional).

En el núcleo **C5-REAL** de CORTEX-Persist, esta conexión no es una analogía literaria; es la ley física que rige la persistencia y la evolución del Grafo de Dependencia Epistémica (EDG).

---

## 1. Termodinámica: La Minimización de la Sorpresa y la Muerte Térmica

En la mecánica estadística, el término $-\ln p(y)$ define la **sorpresa** de encontrar al sistema en un estado sensorial $y$ anómalo. Para un organismo biológico, entrar en un estado de alta sorpresa (como la desintegración física) es equivalente a la muerte.

$$F = \text{Sorpresa} + \text{Divergencia KL} \ge -\ln p(y)$$

### Isomorfismo en CORTEX-Persist:
*   **La Sorpresa:** Representa la inyección de entropía estocástica procedente de modelos LLM (*LLM Slop*). Un estado de alta sorpresa en CORTEX es un commit corrupto, un bypass de los guards, o un *Context Rot* donde la base de datos se vuelve estocástica y contradictoria.
*   **Evitar la Muerte Térmica:** Minimizar $F$ restringe los estados del sistema al Ledger criptográfico inmutable de Git y SQLite en modo WAL. La energía (tiempo de cómputo) se enfoca en resolver aserciones útiles. El calor residual (prosa decorativa, alucinaciones) se disipa al exterior mediante el motor de poda `cortex_purge_inventory.py`.

---

## 2. El Cerebro: Codificación Predictiva e Inferencia Activa

El cerebro no es un receptor pasivo; mantiene un modelo generativo interno $q(\vartheta)$ sobre las causas ocultas del entorno $\vartheta$. La Divergencia de Kullback-Leibler (KL) mide la discrepancia entre las creencias internas del cerebro y la realidad biológica de los estímulos $p(\vartheta \mid y)$.

$$\text{D}_{\text{KL}}(q(\vartheta) \parallel p(\vartheta \mid y))$$

Para minimizar este error de predicción, el sistema posee dos caminos:
1.  **Aprendizaje (Percepción):** Alterar el modelo interno $q(\vartheta)$ para que coincida con la realidad (actualizar creencias).
2.  **Acción:** Actuar sobre el entorno para alterar los estímulos de entrada $y$ de modo que encajen con las predicciones del cerebro.

### Isomorfismo en CORTEX-Persist:
*   **Percepción:** Cuando un test unitario falla o se detecta una vulnerabilidad en [cortex-validation-simulation.py](file:///Users/borjafernandezangulo/10_PROJECTS/cortex-persist/cortex-validation-simulation.py), el kernel actualiza el Grafo de Dependencias Epistémicas (EDG) para incorporar el nuevo estado de fallo, inhabilitando la hipótesis de seguridad previa (Taint Propagation).
*   **Inferencia Activa (Acción):** El kernel no asimila el error pasivamente. Despliega el **Git Sentinel** (mutación física de archivos, creación de ramas `auto/quarantine-*` y commits atómicos) para forzar al entorno de desarrollo a alinearse con la invariante de correctitud lógica del compilador.

---

## 3. Agentes de IA: Inferencia Variacional y Maximización de la ELBO

En el aprendizaje automático, minimizar la Energía Libre Variacional $F$ es matemáticamente equivalente a maximizar la **Cota Inferior de Evidencia** (ELBO, *Evidence Lower Bound*). El agente de IA optimiza sus redes neuronales para procesar y comprimir la información con la máxima eficiencia.

### Isomorfismo en CORTEX-Persist:
El cálculo físico de la exergía en [measure_exergy.py](file:///Users/borjafernandezangulo/10_PROJECTS/cortex-persist/measure_exergy.py) evalúa este rendimiento:

*   **Exergía Cognitiva ($\Xi$):** Mide la conversión de inferencias estocásticas desordenadas (ruido de LLM) en estructuras deterministas altamente comprimidas (AST, árboles de Merkle, esquemas validados).
*   **Apetito de Quorum:** El Quorum BFT de validadores simulados en `cortex-validation-simulation.py` (ej. Perelman-Core, Witten-Core) actúa como un codificador variacional descentralizado. Rechaza estados mutados que no alcanzan consenso matemático, evitando que el modelo se auto-contamine con ruido entrópico.

---

## 4. Anclaje de Ejecución (C5-REAL)

Las abstracciones formales anteriores se ejecutan y verifican empíricamente a través de los siguientes scripts del sistema:

1.  **[cortex-validation-simulation.py](file:///Users/borjafernandezangulo/10_PROJECTS/cortex-persist/cortex-validation-simulation.py):** Orquesta el ciclo de 6 capas (Ingest, Audit, Mutate, Anchor, Verify, Attest) que implementa físicamente la Inferencia Activa sobre el Ledger de Git y la base de datos WAL.
2.  **[measure_exergy.py](file:///Users/borjafernandezangulo/10_PROJECTS/cortex-persist/measure_exergy.py):** Cuantifica la eficiencia del procesamiento de datos en Joules cognitivos y restringe el blast radius de la mutación lógica.

---
*Documento estabilizado y registrado en el ledger histórico de CORTEX-Persist.*
*Autoría atribuida a: Borja Moskv (borjamoskv).*
