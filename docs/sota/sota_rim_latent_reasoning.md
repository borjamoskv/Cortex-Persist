<!-- [C5-REAL] Exergy-Maximized -->
# Estado del Arte (SOTA): Latent Reasoning en LLMs (RiM)

**ID del Artefacto:** `SOTA-2605.30343v1`
**Estado:** C5-REAL (Empíricamente Destilado)
**Fecha de Forja:** 2026-06-01

## 1. Delimitación Temporal
- **Dominio:** Computer Science / Artificial Intelligence (LLM Reasoning / Autonomous Agents).
- **Timeframe:** T-3 días (Publicado el 28 de Mayo de 2026).
- **Fuente:** arXiv:2605.30343v1.

## 2. Matriz Analítica
| Dimensión | Valor |
| :--- | :--- |
| **Autor(es)** | Lukas Aichberger, Sepp Hochreiter |
| **Año** | 2026 |
| **Objetivos** | Desacoplar la computación del razonamiento interno de la generación externa (autoregresiva) para eficientar el escalado de test-time compute. |
| **Metodología** | *Reasoning in Memory (RiM)*: Reemplazo de tokens de "pensamiento" (CoT) explícitos por bloques de memoria latentes (secuencias fijas de tokens especiales) procesados en un solo forward pass, anclados mediante un currículo de dos fases (supervisión explícita -> refinamiento implícito). |
| **Resultados** | Alcanza o supera los métodos de razonamiento latente existentes sin requerir la costosa generación autoregresiva de pensamientos intermedios. |
| **Conclusiones** | Los LLM pueden entrenarse para utilizar su memoria de trabajo como un mecanismo O(1) en términos de longitud de secuencia para el razonamiento latente. |

## 3. Biopsia Crítica
- **Mecanismo Base:** Inyección de secuencias fijas de tokens especiales que actúan como "memoria de trabajo". Al ser secuencias fijas y no generadas autoregresivamente, el LLM procesa el bloque en paralelo durante el *forward pass*, manipulando la información latente sin el desperdicio computacional de la decodificación token por token.
- **Fallo Estructural (Vacío Exérgico):** Chain-of-Thought (CoT) tradicional asume que la cognición debe ser un stream de tokens legibles, lo cual vincula O(N) computación de atención a latencia de generación. RiM resuelve esto. El vacío exérgico restante se traslada al entorno de **Agentes Soberanos**: ¿Cómo podemos instanciar estos *memory blocks* dinámicamente en tiempo de inferencia sin reentrenar la base, o cómo un agente puede auto-gestionar su tamaño de bloque latente en función de la complejidad del entorno?

## 4. Cristalización
El avance de RiM cristaliza la obsolescencia del "thinking out loud" en los LLMs para tareas donde el intermediate state no necesita ser auditable por el humano. Al colapsar la latencia de generación de pensamiento en un único forward pass paralelo sobre tokens especiales, se maximiza la exergía del modelo. Para el ecosistema CORTEX y agentes autónomos, la implicación es directa: el razonamiento interno debe migrar hacia operaciones latentes O(1) de alta densidad de señal, dejando la decodificación autoregresiva estrictamente para el I/O del agente (acciones, API calls, output final).
