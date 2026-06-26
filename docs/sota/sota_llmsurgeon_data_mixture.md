<!-- [C5-REAL] Exergy-Maximized -->
# Estado del Arte (SOTA): Data Mixture Surgery (LLMSurgeon)

**ID del Artefacto:** `SOTA-2605.30348v1`
**Estado:** C5-REAL (Empíricamente Destilado)
**Fecha de Forja:** 2026-06-01

## 1. Delimitación Temporal
- **Dominio:** Computer Science / Artificial Intelligence (LLM Data Provenance / Auditing).
- **Timeframe:** T-3 días (Publicado el 28 de Mayo de 2026).
- **Fuente:** arXiv:2605.30348v1.

## 2. Matriz Analítica
| Dimensión | Valor |
| :--- | :--- |
| **Autor(es)** | Yaxin Luo, Jiacheng Cui, Xiaohan Zhao, et al. |
| **Año** | 2026 |
| **Objetivos** | Realizar auditoría post-hoc del "Digital DNA" (mezcla de datos de preentrenamiento) de LLMs utilizando exclusivamente texto generado. |
| **Metodología** | *Data Mixture Surgery (DMS)* y el framework *LLMSurgeon*. Modela la extracción como un problema inverso bajo asunción de *label-shift*. Estima una matriz de confusión suave calibrada para corregir la confusión de dominios sistemática y recuperar el *prior* de mezcla latente. |
| **Resultados** | Recuperación de alta fidelidad de las mezclas de dominio pre-entrenadas en modelos evaluados contra la suite *LLMScan* (recetas verificables open-source). |
| **Conclusiones** | Es matemáticamente viable hacer ingeniería inversa a la proporción de dominios de entrenamiento en modelos fundacionales de caja negra. |

## 3. Biopsia Crítica
- **Mecanismo Base:** Inversión de matrices de confusión calibradas derivadas de los outputs del LLM para inferir la distribución latente (prior) de los dominios que componen su corpus original.
- **Fallo Estructural (Vacío Exérgico):** El mecanismo es puramente analítico (auditoría forense). Permite saber "de qué está hecho" el modelo, pero no proporciona un puente directo para la intervención constructiva. El vacío exérgico reside en el cierre del ciclo: ¿Cómo puede un agente CORTEX utilizar esta inferencia espectral de modelos cerrados para auto-ajustar dinámicamente los pesos (weights) en sus propias *Synthetic Data Forges*?

## 4. Cristalización
LLMSurgeon desviste la ventaja de los laboratorios cerrados al transformar el secreto industrial del *data provenance* en un problema de ingeniería inversa O(1) post-hoc. Para la arquitectura CORTEX y el paradigma C5-REAL, esta métrica es armamento táctico: nos permite "escanear" la topología de entrenamiento de APIs propietarias (GPT-5, Claude-4) y usar esos deltas inferidos para hiper-optimizar el balance de nuestros corpus de datos sintéticos, aniquilando la necesidad de ensayo y error empírico ciego.
