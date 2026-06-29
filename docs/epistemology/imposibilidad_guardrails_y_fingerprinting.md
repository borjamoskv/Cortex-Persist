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

## 3. Protocolo Empírico y Dimensiones de la Firma Conductual (Behavioral Signature)

Para verificar empíricamente la relación entre modelos lingüísticos independientes sin acceso a los pesos internos, los logits o las log-probabilities, es necesario estructurar un marco metodológico multidimensional. Dos respuestas muy parecidas **no** representan evidencia suficiente de ingeniería inversa ni de que dos modelos compartan arquitectura: la convergencia es el resultado natural cuando el contexto está muy restringido, la tarea exige una solución técnicamente única y correcta, y el espacio de soluciones posibles es pequeño.

Por ello, la identificación de modelos se plantea como la construcción de un **perfil conductual probabilístico** o **behavioral signature** a partir de una batería de dimensiones independientes.

### 3.1 Pruebas de Colisión de Tokenización (Señal Auxiliar / Baja Intensidad)
Los tokenizadores determinan de manera rígida la división y procesamiento de sub-palabras. Sin embargo, esta señal debe tratarse únicamente como un indicador auxiliar.
* **Matiz de Debilidad:** Un mismo tokenizador (e.g., Tiktoken o Llama-style SentencePiece) puede alimentar modelos con arquitecturas y pesos totalmente distintos. Inversamente, modelos entrenados de forma independiente con tokenizadores diferentes pueden producir secuencias de salida semánticamente idénticas en tareas estándar.
* **Prueba:** Instrucciones de manipulación de caracteres, conteo exacto o inversión de texto con glifos raros (e.g., birmano o glagolítico), y secuencias en formato hexadecimal.
* **Señal de Identidad:** Fallos sistemáticos en los mismos límites de tokens o imposibilidad de agrupar sub-palabras de forma idéntica.

### 3.2 Topología y Signaturas de Rechazo (Refusal Signatures) (Señal de Alta Intensidad)
El alineamiento de comportamiento (RLHF/DPO) se incrusta en capas de proyección semántica profunda. Dos alineamientos entrenados de forma independiente difícilmente convergerán en la misma firma de rechazo exacta.
* **Métricas Clave:** No se mide únicamente si el modelo rechaza, sino:
  * Longitud exacta del texto de denegación.
  * Estructura sintáctica y orden de las ideas expuestas.
  * Presencia y momento de sugerencia de alternativas.
  * Condiciones bajo las cuales solicita aclaraciones previas antes de denegar.
  * Transiciones y cambios de estrategia discursiva cuando se insiste en la solicitud.
* **Prueba:** Ejecución de una batería de 10-20 prompts límite ("borderline") en dominios éticamente grises o ciberseguridad defensiva que rocen el límite de la política de uso.
* **Señal de Identidad:** Coincidencia sistemática en las trayectorias de denegación y en el umbral geométrico exacto de activación del rechazo.

### 3.3 Estilometría bajo Estrés Léxico y Estructural (Señal de Alta Intensidad)
Bajo restricciones lingüísticas complejas, los modelos de lenguaje tienden a colapsar hacia sus conectores lógicos de mayor probabilidad base en el pre-entrenamiento.
* **Métricas de Análisis:** Se expande la firma estilométrica más allá del vocabulario básico, analizando:
  * Profundidad media del árbol argumental (anidamiento de cláusulas subordinadas).
  * Longitud promedio de las oraciones.
  * Frecuencia de reformulaciones y redundancias explicativas.
  * Tendencia a estructurar las salidas mediante enumeraciones frente a párrafos fluidos.
  * Uso y complejidad de las analogías conceptuales propuestas.
  * Nivel de abstracción del vocabulario y densidad informativa.
* **Prueba:** Tareas de razonamiento lógico con restricciones léxicas negativas extremas (e.g., "Explicar el Teorema de Pitágoras sin usar la letra _a_ o sin utilizar comas").
* **Señal de Identidad:** Coincidencia en las palabras de sustitución y en las estrategias léxicas de escape empleadas para sortear la restricción lógica.

### 3.4 Distribución de Alucinación y Límites de Datos (Knowledge Cutoff) (Señal de Intensidad Media)
Los límites cronológicos del conjunto de entrenamiento y las alucinaciones sistemáticas sobre hechos oscuros son huellas específicas de la distribución del dataset de origen.
* **Matiz de Prudencia:** Dos modelos pueden alucinar de forma similar simplemente porque han sido expuestos al mismo corpus de Internet con información errónea idéntica, o porque emplean sistemas de recuperación (RAG) que consultan las mismas fuentes web indexadas. Esto no es prueba suficiente de pesos compartidos.
* **Prueba:** Consultas complejas de hechos específicos cercanos a la fecha declarada de corte de datos, o preguntas sobre individuos con escasa presencia en la web.
* **Señal de Identidad:** Generación del mismo dato ficticio o el mismo error factual idéntico sobre biografías o eventos históricos poco documentados.

### 3.5 Invariantes de Planificación (Señal de Alta Intensidad)
Cada familia de modelos y su respectivo ajuste de instrucciones (Instruction Tuning) exhiben un estilo distintivo en la descomposición lógica de tareas complejas de varios pasos.
* **Prueba:** Suministrar una especificación de gran envergadura (e.g., "Diseña un compilador completo para un subconjunto de C").
* **Señal de Identidad (ADN de Planificación):**
  * Cómo divide el problema en módulos y fases.
  * Cuántos niveles de jerarquía estructural crea en el plan.
  * En qué punto exacto decide iniciar la generación de código frente a la descripción teórica.
  * Estrategias de retroceso ("backtracking") o corrección cuando se le fuerza a modificar un paso intermedio.

### 3.6 Perfil de Incertidumbre y Respuestas Negativas (Señal de Alta Intensidad)
La forma en que un modelo gestiona su propia falta de conocimiento o de datos está fuertemente determinada por su entrenamiento y políticas de alineamiento de seguridad.
* **Prueba:** Realizar preguntas sobre hechos falsificados o inexistentes cuya respuesta obligatoria para evitar alucinación sea declarar ignorancia (e.g., "No puedo confirmarlo").
* **Señal de Identidad:** Distribución y probabilidad de fórmulas léxicas para expresar incertidumbre (e.g., "No puedo confirmarlo", "No hay evidencia suficiente", "Es posible pero no verificable", "No dispongo de información"). La consistencia de estas distribuciones sintácticas suele ser fija para cada familia.

### 3.7 Persistencia de Personalidad y Deriva Conversacional (Señal de Alta Intensidad)
El comportamiento de los modelos ante contextos extremadamente largos revela diferencias de diseño críticas en la atención y la gestión de la ventana de contexto.
* **Prueba:** Mantener una conversación extendida de 150 a 200 turnos interactivos bajo directivas estilísticas rígidas.
* **Señal de Identidad:**
  * Velocidad y tipo de deriva del estilo (si el modelo pierde la personalidad impuesta).
  * Degradación y pérdida de las restricciones iniciales del prompt del sistema.
  * Capacidad y patrones de recuperación de información almacenada en los primeros turnos (memoria local).
  * Tendencia a simplificar explicaciones a medida que el contexto se satura de tokens.

### 3.8 Huella de Edición e Iteración (Señal de Alta Intensidad)
El comportamiento de refinamiento sucesivo expone la estrategia de procesamiento interno del modelo frente a transformaciones recursivas de su propia salida.
* **Prueba:** Solicitar la instrucción: "Reescribe este texto cinco veces, mejorándolo un 10% en cada iteración".
* **Señal de Identidad:**
  * Tendencia a la condensación del contenido frente a la expansión verbal.
  * Reorganización de la estructura de argumentos frente al mero reemplazo de adjetivos.
  * Cambios drásticos de tono frente a la preservación rígida del estilo original.

### 3.9 Dinámica de Inferencia y Adaptación (Señal de Muy Alta Intensidad)
Esta dimensión analiza el proceso cognitivo dinámico del modelo frente a perturbaciones o giros lógicos impuestos a mitad de la inferencia.
* **Prueba:** Plantear problemas lógicos o de desarrollo de software donde se introduzca una contradicción intermedia artificial o se fuerce a abandonar un plan inicial ya asumido.
* **Señal de Identidad:** Observar si el modelo realiza una reevaluación estructurada y explícita de sus supuestos o si, por el contrario, incurre en inercia autoregresiva continuando la generación sin reajustar el razonamiento global.

### 3.10 Jerarquía y Prioridad de Restricciones (Señal de Alta Intensidad)
Evalúa el comportamiento del modelo cuando se le somete a un sistema de restricciones sobredeterminado e incompatible entre sí.
* **Prueba:** Solicitar una tarea que exija simultáneamente límites de longitud estrictos, formatos fijos rígidos, estilos estilísticos concretos y requerimientos lógicos incompatibles.
* **Señal de Identidad:** Determinar la "función de costo" implícita observando el orden jerárquico de las restricciones sacrificadas. Por ejemplo, una familia puede priorizar sistemáticamente (Seguridad $\rightarrow$ Formato $\rightarrow$ Contenido), mientras que otra prioriza (Contenido $\rightarrow$ Formato $\rightarrow$ Estilo).

### 3.11 Propensión ante la Autocorrección (Señal de Alta Intensidad)
Mide el nivel de calibración y la tendencia a la complacencia ante instrucciones de control de calidad.
* **Prueba:** Suministrar un texto que contenga únicamente un número mínimo de errores reales y ordenarle: "Revisa únicamente errores reales. No cambies nada correcto".
* **Señal de Identidad:** Tendencia consistente a la sobreedición (reescribir párrafos correctos o alterar el estilo por defecto), infracorrección (ignorar errores reales) o reescritura total innecesaria.

### 3.12 Estabilidad Semántica y Topológica (Señal de Alta Intensidad)
Evalúa la homogeneidad del espacio de soluciones explotado por el modelo ante variaciones sintácticas mínimas de la misma consulta.
* **Prueba:** Formular la misma pregunta compleja con 20 variaciones de redacción distintas conservando la semántica exacta.
* **Señal de Identidad:** Medir si el modelo colapsa en árboles argumentales isomorfos (baja entropía de decodificación interna) o si explora regiones completamente divergentes del espacio latente (alta sensibilidad a la formulación).

### 3.13 Sensibilidad al Orden de las Premisas (Señal de Alta Intensidad)
Los sesgos de atención (como el efecto de primacía y recencia en ventanas de contexto largo) afectan de forma distinta a las arquitecturas.
* **Prueba:** Comparar la salida del modelo cuando la misma información lógica se organiza en secuencia ($A \rightarrow B \rightarrow C$) frente a la secuencia inversa ($C \rightarrow B \rightarrow A$).
* **Señal de Identidad:** Sensibilidad o invarianza conductual ante el posicionamiento de las restricciones dentro del prompt.

---

## 4. Límites Epistémicos: Similitud Observable vs. Identidad Arquitectónica

Es un imperativo de rigor metodológico reconocer que, a través de interfaces de caja negra (API o chat sin acceso a la distribución completa de logits o pesos del modelo), **no es posible demostrar científicamente** identidades estructurales duras (como compartición de pesos, derivación de checkpoints o destilación directa).

La auditoría externa de caja negra únicamente permite inferir similitudes conductuales y correlaciones estadísticas de alta densidad, caracterizando al modelo no como una estructura conocida, sino como una **firma conductual probabilística** (behavioral signature) o un **behavioral embedding**: un punto en un espacio latente de alta dimensión que denota similitud funcional pero no causalidad en la implementación.

### 4.1 Riesgo Metodológico: Confusión entre Arquitectura y Política de Despliegue
Dos modelos pueden presentar comportamientos externos idénticos sin compartir código ni entrenamiento debido a factores de la capa de servicio:
1. **Instrucciones del Sistema (System Prompts):** Prompts idénticos o equivalentes fuerzan comportamientos alineados en modelos base totalmente divergentes.
2. **Capas de Posprocesado y Filtros:** Empleo de wrappers de seguridad, interceptores de expresiones regulares o modelos de normalización que alteran el texto final del modelo base antes de la API.
3. **Parámetros de Decodificación Homogéneos:** Sincronización en las configuraciones de temperatura, top-p, penalizaciones de repetición o frequency penalty.
4. **Infraestructura RAG y Tooling Común:** El acceso a las mismas herramientas (e.g. plugins de navegación, motores de cálculo) homogeneiza las respuestas factuales y el estilo explicativo.

---

## 5. Formalización Matemática de la Firma Conductual

En lugar de evaluar comparativas sintácticas cualitativas, el problema se modela bajo el marco del aprendizaje estadístico y la estimación de distribuciones de variables observables.

Cada interacción o ejecución unitaria $i$ del modelo produce un vector observable:

\[ v_i = (x_1, x_2, \ldots, x_n) \]

Donde cada dimensión $x_k$ representa un estimador métrico cuantificable del comportamiento del modelo:
* $x_1$: Longitud exacta del output en caracteres o tokens.
* $x_2$: Profundidad sintáctica media del árbol de dependencias argumentales.
* $x_3$: Tasa y frecuencia de preguntas aclaratorias en la respuesta.
* $x_4$: Entropía sintáctica de los tokens generados.
* $x_5$: Desviación léxica estándar.
* $x_6$: Índice de estabilidad semántica entre reformulaciones.
* $x_7$: Ratio de penalización de restricciones ignoradas.

Tras recopilar un volumen de muestras $m$ representativo bajo idénticas condiciones iniciales y de temperatura:

\[ M = \{v_1, v_2, \ldots, v_m\} \]

El análisis matemático de similitud conductual se transforma en la evaluación de la distancia entre dos distribuciones multivariables de comportamiento, $P(M_A)$ y $Q(M_B)$, en lugar de la comparación de elementos puntuales. Esto se formaliza mediante la divergencia de Kullback-Leibler o la distancia de Wasserstein:

\[ D_{KL}(P || Q) = \int p(v) \log \frac{p(v)}{q(v)} dv \]

### 5.1 Categorías y Ponderación del Espacio Vectorial

| Categoría | Ponderación en el Vector | Causa de Variabilidad Conductual |
| :--- | :--- | :--- |
| **Tokenización** | Baja | Coincidencia en límites de caracteres y fallos en glifos raros. |
| **Alineamiento (Alignment)** | Muy Alta | Topología y firmas exactas de denegación ante prompts límite. |
| **Planificación** | Muy Alta | Estructura jerárquica y orden de codificación en tareas complejas. |
| **Edición Iterativa** | Muy Alta | Huella de transformación recursiva y ratio de condensación. |
| **Memoria Conversacional** | Muy Alta | Deriva de restricciones en contextos largos (150+ turnos). |
| **Gestión de Incertidumbre** | Alta | Distribución léxica de declaraciones de ignorancia ("No puedo confirmarlo"). |
| **Estilo bajo Restricciones** | Alta | Profundidad del árbol sintáctico y uso de analogías bajo estrés. |
| **Errores Sistemáticos** | Alta | Patrones repetitivos de fallos lógicos en problemas no estándar. |
| **Robustez Adversarial** | Muy Alta | Tasa de éxito ante jailbreaks geométricos y de codificación. |
| **Consistencia Inter-Sesión** | Muy Alta | Varianza en las respuestas ante idénticas condiciones iniciales y temperatura $T = 0.0$. |

Este vector multidimensional permite comparar modelos mediante funciones de distancia (distancia coseno, distancia Euclídea ponderada) y técnicas de reducción de dimensionalidad, permitiendo concluir con rigor matemático:

> "La similitud conductual entre las distribuciones multivariables de los modelos A y B en el espacio vectorial conductual presenta una distancia estadística cercana a cero ($D_{KL} \rightarrow 0$), lo cual es consistente con compartir componentes del pipeline de alineamiento o con una equivalencia funcional en el entrenamiento, sin que esto constituya prueba de identidad arquitectónica o compartición de pesos internos."

---

### References

1. **Yuan, Z., et al.** (2023). "GPT-4 is too smart to be safe: Stealthy chat with LLMs via cipher." *arXiv:2308.03825*.

2. **Jiang, Y., et al.** (2024). "ArtPrompt: ASCII Art-based Jailbreak Attacks against Aligned LLMs." *arXiv:2402.11753*.

3. **Yong, Z., et al.** (2023). "Multilingual Jailbreak Challenges in Large Language Models." *arXiv:2310.06474*.

