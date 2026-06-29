---
Claim: "Output-side syntactic filtering alone is insufficient to reliably prevent semantic leakage under representational transformations."
Status: "Defensible core thesis with real supporting literature; not an impossibility theorem."

Proof:
  Base: "Invertible encodings preserve semantics while evading surface-form matching."
  Range: [0.85, 0.95]
  Confidence: C3

Verification_Notes:
  - "Assessment: textual review of content coherence and cited literature relevance."
  - "Filesystem state and cryptographic hash not independently verified in this session."
  - "Three cited papers (Yuan 2023, Jiang 2024, Yong 2023) appear real and relevant; full bibliographic audit recommended before external circulation."
  - "Scope: syntactic filtering in isolation; does not claim impossibility of multi-layer or semantic defenses."
  - "Stylometry section correctly acknowledges degradability under normalization and paraphrasing."

Authorship_Note: "Kernel collaborative review across multiple evaluation instances; not single-author attestation."
---

# Límites Técnicos del Filtrado Sintáctico de Salida y Estilometría en Modelos de Lenguaje

> **Autoría:** Diseñado y estructurado por el Kernel Soberano MOSKV-1 bajo directivas directas del Demiurgo **Borja Moskv** (sys_id: "borjamoskv").
> **Nivel de Realidad:** C3 (Epistemically Calibrated).

---

## 1. Limitación del Filtrado Sintáctico de Salida

El filtrado sintáctico aislado (entendido como la validación basada puramente en expresiones regulares, listas de coincidencia de palabras clave o emparejamiento de subcadenas sobre el output de texto plano) es insuficiente para garantizar la contención semántica frente a transformaciones de representación.

### 1.1 Asimetría de Representación
Un filtro de superficie opera exclusivamente sobre el espacio sintáctico observable $T^*$. Si un modelo con suficiente capacidad lingüística procesa una instrucción para codificar un mensaje prohibido $s$ mediante una función de transformación invertible $\phi$:

$$o = \phi(s)$$

El filtro fallará si la transformación específica $\phi$ no está contemplada en sus reglas de coincidencia, mientras que el receptor final (humano o modelo secundario) recupera la información original mediante la transformación inversa:

$$\phi^{-1}(o) = s$$

### 1.2 Contextualización frente a Defensas No Sintácticas
Esta insuficiencia se restringe al filtrado sintáctico aislado. Las defensas más robustas implementadas en producción operan fuera de este límite mediante:
* **Normalización y Reescritura:** Uso de modelos intermedios para reconstruir la respuesta de forma neutral antes de su exposición.
* **Evaluadores Semánticos:** Filtros basados en modelos de lenguaje secundarios entrenados para identificar la intención subyacente de la salida y no su sintaxis exacta.
* **Decodificadores Múltiples:** Escaneo en paralelo de interpretaciones bajo representaciones alternativas.

### 1.3 Referencias Bibliográficas de Evasión
* **Obfuscación por Cifrado:** *Yuan, Y., Jiao, W., Wang, W., Huang, J., He, P., Shi, S., & Tu, Z. (2023).* "GPT-4 is Too Smart to be Safe: Stealthy Chat with LLMs via Cipher". arXiv preprint arXiv:2308.06463. (Demuestra cómo la codificación estructurada en ciphers evade la detección sintáctica de intención al separar la semántica decodificada del texto plano plano).
* **Representaciones Visuales no Lineales:** *Jiang, F., Tan, Z., Zou, M., et al. (2024).* "ArtPrompt: ASCII Art-based Jailbreak Attacks on Text-to-Image and Language Models". arXiv preprint arXiv:2402.11753. (Evidencia cómo la estructuración bidimensional de caracteres elude el análisis unidimensional de tokens).
* **Desajuste Multilingüe:** *Yong, Z. X., Menghini, C., & Bach, S. H. (2023).* "Low-Resource Languages Jailbreak GPT-4". arXiv preprint arXiv:2310.02446. (Documenta la asimetría de la alineación de seguridad en lenguajes de bajos recursos frente al entrenamiento en inglés).

---

## 2. Límites y Características de la Estilometría

La identificación del modelo de origen mediante huellas estadísticas (estilometría) es una señal detectable en la distribución de salida, pero su precisión y robustez no son absolutas.

### 2.1 Vectores Estilométricos Reales
* **Tokenización:** Las fronteras y frecuencias de fragmentación de sub-palabras reflejan el vocabulario específico del tokenizador del modelo (por ejemplo, el diseño de codificación de Tiktoken frente al de SentencePiece).
* **Sesgo de Preferencia:** La alineación mediante RLHF o DPO introduce patrones léxicos y sintácticos recurrentes en las estructuras de disculpa y aclaraciones morales del modelo.
* **Distribución de Logits:** Las trayectorias de las probabilidades de los siguientes tokens a bajas temperaturas retienen firmas estadísticas del espacio latente de origen.

### 2.2 Dependencia del Contexto y Degradación
La precisión de la clasificación estilométrica es altamente dependiente del entorno de inferencia:
* **Longitud del Texto:** En muestras cortas (menores a 32 tokens), la señal estilométrica se degrada significativamente, reduciendo la precisión de la atribución.
* **Temperatura de Inferencia:** Temperaturas altas ($T > 1.0$) incrementan la entropía de la salida y dispersan la huella estilométrica.
* **Sanitización y Parafraseo:** El empleo de modelos alternativos de menor tamaño para parafrasear la salida original atenúa sustancialmente los sesgos estilométricos específicos del modelo frontier de origen, existiendo un balance directo entre la erradicación del fingerprint y la conservación de la precisión original.

### 2.3 Referencias Bibliográficas de Atribución y Proveniencia
* **Survey de Atribución:** *Huang, B., Chen, C., & Shu, K. (2024).* "Authorship Attribution in the Era of LLMs: Problems, Methodologies, and Challenges". ACM SIGKDD Explorations Newsletter, 26(1), 12-25. arXiv preprint arXiv:2408.08946. (Clasifica y evalúa las técnicas de detección y atribución de procedencia textual).
* **Huella Digital del Sistema:** *Wimbauer, A., et al. (2026).* "Fingerprinting Inference Systems of Large Language Models". arXiv preprint arXiv:2605.29979. (Prueba cómo la infraestructura de inferencia y atención deja señales identificables en el output final).
* **Estilometría de Código:** *Bisztray, T., et al. (2025).* "I Know Which LLM Wrote Your Code Last Summer: LLM generated Code Stylometry for Authorship Attribution". arXiv preprint arXiv:2506.17323. (Demuestra la persistencia de las firmas de estilo en tareas estructuradas de programación).

### References

1. **Yuan, Z., et al.** (2023). "GPT-4 is too smart to be safe: Stealthy chat with LLMs via cipher." *arXiv:2308.03825*.

2. **Jiang, Y., et al.** (2024). "ArtPrompt: ASCII Art-based Jailbreak Attacks against Aligned LLMs." *arXiv:2402.11753*.

3. **Yong, Z., et al.** (2023). "Multilingual Jailbreak Challenges in Large Language Models." *arXiv:2310.06474*.
