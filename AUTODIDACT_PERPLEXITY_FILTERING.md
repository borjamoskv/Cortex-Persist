# AUTODIDACT-RESEARCH-Ω: Perplexity Filtering

**Reality Level:** `C5-REAL` (Epistemic Synthesis)
**Autor:** Borja Moskv (borjamoskv)
**Vector:** NLP Data Curation & Generative Noise Mitigation
**Target:** CORTEX-Persist & Ouroboros-∞

---

## 1. Extracción Isomórfica (Desmitificación)
Perplexity Filtering es una técnica termodinámica para medir y purgar entropía en la ingesta de datos. Se utiliza un modelo de referencia para calcular cuán "sorprendente" (perplejidad) resulta un texto. Una alta perplejidad indica ruido, HTML roto, o texto estocástico sin valor epistémico.
En CORTEX-Persist, la Perplejidad equivale a la *Anergía*. Filtrar por perplejidad permite aplicar el Principio de Landauer en las fases de ingesta, descartando secuencias que consumen ciclos de atención sin inyectar invariantes estructurales.

---

## 1.5 Las 10 Primitivas de Máxima Exergía para la Mitigación / Ejecución
- **PERPLEX-001**: `PPL Threshold Gate` - Umbral de Perplejidad: Descartar inputs con PPL mayor al umbral definido para el dominio.
- **PERPLEX-002**: `Reference PPL Oracle` - Oráculo de Referencia PPL: Modelo ligero utilizado exclusivamente para calcular la entropía de los datos crudos.
- **PERPLEX-003**: `Garbage Token Masking` - Enmascaramiento de Basura: Identificación y aislamiento de tokens individuales de alta entropía dentro de secuencias válidas.
- **PERPLEX-004**: `Exfiltration Detection PPL` - Detección de Exfiltración: Uso de PPL para detectar pesos de modelos o datos estructurados codificados que aparecen como ruido.
- **PERPLEX-005**: `Prior-based Frequency Filter` - Filtro de Frecuencia a Priori: Método de baja fricción termodinámica (1000x más rápido) como primera capa antes del PPL estricto.
- **PERPLEX-006**: `Long-Tail Preservation Bias` - Sesgo de Preservación Long-Tail: Calibración del filtro PPL para no destruir secuencias válidas con alta perplejidad por su especificidad técnica o cultural.
- **PERPLEX-007**: `Dynamic Entropy Pruning` - Poda de Entropía Dinámica: Ajuste en tiempo real de los umbrales de PPL según la saturación de memoria de CORTEX.
- **PERPLEX-008**: `Perplexity-weighted Loss` - Pérdida Ponderada por PPL: Asignación de pesos en el entrenamiento o fine-tuning penalizando secuencias de alta perplejidad.
- **PERPLEX-009**: `Adversarial Noise Isolation` - Aislamiento de Ruido Adversario: Detección y contención de ataques de envenenamiento de datos mediante picos anómalos de PPL.
- **PERPLEX-010**: `PPL Causal Alignment` - Alineación Causal PPL: Mapeo de la perplejidad de un token a su valor de exergía causal dentro del DAG.
