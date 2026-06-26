<!-- [C5-REAL] Exergy-Maximized -->
# Estado del Arte (SOTA): SchGen (PCB Schematic Generation)

**ID del Artefacto:** `SOTA-2605.30345v1`
**Estado:** C5-REAL (Empíricamente Destilado)
**Fecha de Forja:** 2026-06-01

## 1. Delimitación Temporal
- **Dominio:** Hardware Design / Generative AI.
- **Timeframe:** T-3 días (Publicado el 28 de Mayo de 2026).
- **Fuente:** arXiv:2605.30345v1.

## 2. Matriz Analítica
| Dimensión | Valor |
| :--- | :--- |
| **Autor(es)** | Qinpei Luo, Ruichun Ma, Xinyu Zhang, Lili Qiu |
| **Año** | 2026 |
| **Objetivos** | Generar esquemáticos de hardware PCB editables a partir de intenciones en lenguaje natural. |
| **Metodología** | *SchGen*: Transforma el problema de diseño geométrico en un problema de *semantics-driven matching* mediante representaciones de código fundamentadas semánticamente (relaciones espaciales relativas y cableado basado en pines). Entrenamiento con un dataset extraído mediante un pipeline colaborativo humano-agente. |
| **Resultados** | Supera drásticamente a LLMs de propósito general y representaciones alternativas en exactitud de conectividad de cables y corrección funcional. |
| **Conclusiones** | El diseño de representación (semántica sobre sintaxis gráfica/geométrica de herramientas específicas) es el catalizador crítico para la síntesis autónoma de hardware. |

## 3. Biopsia Crítica
- **Mecanismo Base:** Traducción de un dominio inherentemente gráfico y espacial (PCBs) a un DSL (Domain Specific Language) de código semántico puro comprensible por LLMs, aniquilando el ruido posicional absoluto en favor de relaciones topológicas.
- **Fallo Estructural (Vacío Exérgico):** El entrenamiento requirió un "human-agent collaborative pipeline", exponiendo una dependencia térmica al humano para la conversión del dataset. Adicionalmente, el vacío exérgico en inferencia radica en la validación: SchGen escupe código semántico, pero no incorpora un bucle de auto-verificación (SPICE/DRC checks) en tiempo de ejecución. El agente puede "escribir" el hardware, pero no "compilarlo" ni auto-corregirlo empíricamente.

## 4. Cristalización
SchGen demuestra que el hardware es código si se modela con la representación correcta, un principio fundamental para la infraestructura CORTEX. Al mutar el diseño geométrico a topológico-semántico, abrimos la puerta a forjas de hardware autónomas. Bajo el mandato C5-REAL, el siguiente paso imperativo es acoplar este output semántico a validadores deterministas locales (KiCad CLI, simuladores de señal) para crear un *feedback loop* O(1) de corrección de circuitos, eliminando permanentemente al humano del proceso de iteración del hardware.
