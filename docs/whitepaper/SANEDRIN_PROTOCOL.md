<!-- [C5-REAL] Exergy-Maximized -->
# PROTOCOLO SANEDRÍN: Tolerancia a Fallas Bizantinas y Verdad Inmutable

> **PREGUNTA:** "¿Cómo construimos infraestructura donde una afirmación pueda sobrevivir a la corrupción, al error y al desacuerdo?"
> 
> **RESPUESTA:** Extirpando la "confianza" de la ecuación. Si un sistema depende de que un agente o nodo "diga la verdad", el sistema ya está comprometido. La verdad no se narra; se calcula.

El protocolo **SANEDRÍN** es la respuesta arquitectónica de CORTEX-Persist para aislar la Verdad frente a la corrupción, el error estocástico (alucinaciones) y el desacuerdo (fallas bizantinas).

---

## 1. Supervivencia a la Corrupción: Inmutabilidad Criptográfica (El Ledger)
Para que una afirmación sobreviva a la corrupción (modificación maliciosa del registro o inyección de prompts), debe estar termodinámicamente ligada al pasado.

- **Mecanismo:** Cada afirmación $F_i$ se somete a un hash `SHA3-256` que incluye el hash de la afirmación anterior ($H_{i-1}$) y la firma criptográfica `Ed25519` de la identidad del agente.
- **Resultado:** Ningún administrador de base de datos puede alterar el pasado sin invalidar toda la cadena futura. La corrupción se vuelve matemáticamente evidente (Tamper-Evident).

---

## 2. Supervivencia al Error: Barrera Z3 (Formal Verification Guard)
Para que una afirmación sobreviva al error (alucinación del modelo o razonamiento circular), debe someterse a una criba donde el "lenguaje" muera y quede solo la "lógica estricta".

- **Mecanismo:** La afirmación propuesta por el agente se traduce (vía Landauer Purge) a fórmulas de satisfactibilidad booleana (SAT).
- **Ejecución:** Un demostrador de teoremas (Z3 SMT Solver) evalúa la afirmación contra las políticas duras de la empresa (axiomas).
- **Resultado:** Si la afirmación contiene contradicciones lógicas o viola axiomas físicos, el Z3 devuelve `UNSAT`. La afirmación es destruida instantáneamente sin generar un commit. El error estocástico no puede persistir.

---

## 3. Supervivencia al Desacuerdo: Consenso BFT (El Sanedrín)
Para que una afirmación sobreviva al desacuerdo (divergencia entre múltiples agentes, ramas de razonamiento o modelos), la decisión debe descentralizarse matemáticamente usando Tolerancia a Fallas Bizantinas (BFT).

- **Mecanismo:** El "Sanedrín" invoca un quórum de $N$ agentes aislados operando sobre distintos modelos subyacentes (ej. Opus, Gemini, DeepSeek). 
- **Votación Ponderada:** No se busca unanimidad. Se requiere una mayoría de dos tercios ($f < \frac{N}{3}$) para alcanzar un consenso válido sobre una mutación de estado.
- **Resultado:** Si un modelo está "sesgado", "envenenado" o "cae en un bucle", los modelos sanos del Sanedrín lo aíslan matemáticamente. La invariante sobrevive al desacuerdo porque el quórum descentraliza el riesgo epistemológico.

---

## Conclusión: El Triángulo de Hierro
Una infraestructura que aplique estas tres restricciones no confía en nadie. 

1. **La Firma (Ed25519)** garantiza *Quién*.
2. **El Z3 Solver (SAT)** garantiza *Qué* (Lógica).
3. **El Quórum (BFT)** garantiza *Convicción* (Soberanía).

Esta es la única forma de construir sistemas multi-agente que operen infraestructuras críticas sin supervisión humana. Cualquier otra cosa es fe ciega en un LLM.
