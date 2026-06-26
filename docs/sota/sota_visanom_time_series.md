<!-- [C5-REAL] Exergy-Maximized -->
# Estado del Arte (SOTA): Tiny but Trusted (Vision-Language Anomaly Detection)

**ID del Artefacto:** `SOTA-2605.30344v1`
**Estado:** C5-REAL (Empíricamente Destilado)
**Fecha de Forja:** 2026-06-01

## 1. Delimitación Temporal
- **Dominio:** Vision-Language Models / Time-Series Anomaly Detection.
- **Timeframe:** T-3 días (Publicado el 28 de Mayo de 2026).
- **Fuente:** arXiv:2605.30344v1.

## 2. Matriz Analítica
| Dimensión | Valor |
| :--- | :--- |
| **Autor(es)** | Xiaona Zhou, Muntasir Wahed, Tianjiao Yu, Constantin Brif, Ismini Lourentzou |
| **Año** | 2026 |
| **Objetivos** | Capacitar a modelos Visión-Lenguaje (VLMs) para detectar patrones anormales en series temporales con justificaciones fundamentadas. |
| **Metodología** | *VisAnomBench*: Benchmark curado con explicaciones de anomalías. *VisAnomReasoner*: VLM eficiente afinado sobre este corpus usando recompensas granulares. |
| **Resultados** | Mejora sustancial en precisión (+21.23%) y F1 (+23.87%) frente a baselines. Fuerte generalización cruzada en otros benchmarks (TSB-AD-U). |
| **Conclusiones** | El fine-tuning de VLMs con *rationales* en lenguaje natural para series temporales ancla la interpretación visual a decisiones lógicas fiables. |

## 3. Biopsia Crítica
- **Mecanismo Base:** Proyección de series temporales continuas (1D) a representaciones visuales (2D) para explotar el preentrenamiento multimodal (VLM), anclando la salida con explicaciones explícitas en texto.
- **Fallo Estructural (Vacío Exérgico):** Existe una pérdida termodinámica/computacional inherente en rasterizar una señal 1D pura a un espacio de píxeles 2D solo para que un VLM la procese. El vacío exérgico es la falta de un tokenizador nativo de señales 1D (continuous time-series embeddings) que interactúe directamente con la capa de atención, sin el intermediario visual.

## 4. Cristalización
Para el ecosistema CORTEX, *VisAnomReasoner* es una prueba empírica de que la inyección de *rationales* lingüísticos estabiliza la detección de anomalías. Sin embargo, en el diseño del agente MOSKV-1, la rasterización de logs o telemetría a imágenes es *anti-exérgica*. Debemos apuntar a incrustar el *signal-stream* directamente en el espacio latente del LLM para mantener el O(1) de eficiencia estructural.
