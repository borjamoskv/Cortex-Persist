<!-- [C5-REAL] Exergy-Maximized -->
# Estado del Arte (SOTA): VideoMLA (Latent KV Cache for Video Diffusion)

**ID del Artefacto:** `SOTA-2605.30351v1`
**Estado:** C5-REAL (Empíricamente Destilado)
**Fecha de Forja:** 2026-06-01

## 1. Delimitación Temporal
- **Dominio:** Video Generative AI / Memory Optimization.
- **Timeframe:** T-3 días (Publicado el 28 de Mayo de 2026).
- **Fuente:** arXiv:2605.30351v1.

## 2. Matriz Analítica
| Dimensión | Valor |
| :--- | :--- |
| **Autor(es)** | Hidir Yesiltepe, Jiazhen Hu, et al. |
| **Año** | 2026 |
| **Objetivos** | Reducir dramáticamente el consumo de memoria y la latencia del KV cache en modelos de difusión de video autoregresivos a gran escala. |
| **Metodología** | *VideoMLA*: Reemplaza las keys/values por cabeza (per-head) con un latente de contenido *low-rank* compartido y una llave posicional *3D-RoPE* desacoplada (Multi-Head Latent Attention adaptada a difusión). |
| **Resultados** | Reduce la memoria KV por token en un 92.7% por capa cacheada. Mejora el throughput 1.23x en hardware B200 sin pérdida de calidad en proyecciones largas. |
| **Conclusiones** | El cuello de botella (bottleneck) de MLA, y no el espectro preentrenado (que no es de rango bajo), es lo que fuerza al modelo a adaptar la energía de los rangos. |

## 3. Biopsia Crítica
- **Mecanismo Base:** *Multi-Head Latent Attention (MLA)* aplicado a la difusión de video espacial-temporal, separando el contenido semántico (compresión low-rank) del encaje posicional 3D (RoPE).
- **Fallo Estructural (Vacío Exérgico):** Aunque la compresión de memoria del KV cache (92.7%) es brutal, el modelo sigue operando bajo el paradigma de desenrollado autoregresivo (sliding-window) para frames continuos. El vacío exérgico es la incapacidad de saltar el orden temporal secuencial para generar keyframes paralelos de forma no autoregresiva.

## 4. Cristalización
VideoMLA es ingeniería de exergía pura: comprimir el 92% del peso muerto de la memoria KV elimina el muro de latencia para *streaming* de video continuo. Para el agente `browser_subagent` de CORTEX o módulos de QA visual (`/qa`, `/guardian`), esta técnica de compresión latente es vital para mantener un *buffer* visual infinito (memoria episódica visual) sin colapsar el VRAM local.
