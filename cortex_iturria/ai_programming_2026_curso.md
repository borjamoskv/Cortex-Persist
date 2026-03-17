# 🧠 KNOWLEDGE MEMO: Inteligencia Artificial para Programadores 2026

**Origen**: YouTube Transcript (`2aN_-m1uU4k`)
**Fecha de Ingesta**: 2026-03-07
**Motor de Extracción**: Arakatu (CORTEX Sovereign Ingestion)

---

## 🌌 Axiomas y Conceptos Fundamentales

1. **La Ceguera del Operador**: Programar con IA sin entender su funcionamiento subyacente es "programar a ciegas". El entendimiento del motor es prerrequisito para la maestría.
2. **El Paradigma Finito (Tokens vs Texto)**: Los LLMs no procesan palabras, procesan **Tokens**. La eficiencia de un agente no se mide en caracteres, sino en economía de tokens. (Ej: El alemán o español consumen más tokens que el inglés; `hola mundo` vs `hello world`).
3. **Context Window (La Memoria a Corto Plazo)**: Todo modelo está limitado por su ventana de contexto (ej. 200k tokens). Cada archivo leído, comando ejecutado o MCP cargado consume espacio. La higiene de contexto (Compactación) es obligatoria en flujos largos.

## ⚙️ Arquitectura de Entrenamiento (Las 3 Fases)

1. **Pre-entrenamiento (GPU Fire)**: Consumo masivo de datos crudos (Internet, GitHub) para predecir el siguiente token. Aquí el modelo aprende patrones estadísticos y gramática.
2. **Fine-Tuning (Ajuste Fino)**: Estructuración del conocimiento en formato Conversación/Instrucción (Q&A) para que el modelo sea útil y siga órdenes.
3. **RLHF (Reinforcement Learning from Human Feedback)**: Refinamiento del comportamiento para evitar contenido dañino, mejorar la utilidad y alinear respuestas mediante evaluadores (humanos o IA de control).

## 🦾 El Agente Soberano (Más allá del LLM)

Un LLM es **reactivo** (responde a un prompt). Un Agente es **autónomo**:
- Está insertado en un bucle de ejecución.
- Utiliza **Tools** (Herramientas).
- Observa, Decide y Repite hasta que la tarea se completa (Ej: Agentes de VS Code, Cursor, Claude Code).

### Herramientas de Vanguardia 2026

*   **Cloud Code**: Agente de terminal ligero y extremadamente potente. Brilla en migraciones masivas y refactors sin interfaz gráfica sobrecargada.
*   **Editor-Integrated (Cursor, VS Code con Copilot)**: Integración profunda con el codebase. Capacidades de "Live Coding" con sub-agentes asíncronos en background (`@workspace`, `#files`).
*   **Ejecución Local (Ollama, OpenCode)**: Modelos ligeros (Ej: GLM 4.7 Flash, Qwen) corriendo 100% en privado, consumiendo GPU local pero eliminando el coste por token.

---

## 🧩 Agent Skills vs. MCPs (La Distinción Crítica)

> [!WARNING]
> La confusión entre MCPs y Skills es el error arquitectónico más común en orquestación de Agentes.

| Concepto | Naturaleza | Definición | Implementación |
| :--- | :--- | :--- | :--- |
| **MCP** (Model Context Protocol) | **Funcionalidad** | *Brazos y Ojos*. Herramientas externas que permiten al agente realizar acciones físicas (Ej: Controlar Chrome, leer API de TicketTailor, leer GitHub). | Conexión directa a servidores externos. Requiere Auth. |
| **Agent Skills** | **Conocimiento** | *Cerebro y Experiencia*. Módulos reutilizables de contexto (`.md`) cargados **bajo demanda**. (Ej: Cómo diseñar Frontend, cómo auditar seguridad). | Directorio `.cloud/skills`. El agente decide si necesita leer la skill según la tarea. Peligro de Prompt Injection. |

## 📚 Ecosistema RAG & Síntesis (NotebookLM)
Herramientas como **NotebookLM** abstraen la arquitectura RAG en "Cuadernos". Permiten ingestar PDFs, webs y vídeos para crear un asistente que responde **100% acotado a las fuentes**, mitigando alucinaciones. Generan outputs derivados: Audio-podcast, test de estudio interactivas y mapas mentales.

---

```derivation
DERIVATION: Ω₁ (Multi-Scale Causality) + Ω₅ (Antifragile by Default)
La separación entre Skills (metaconocimiento condicional) y MCPs (actuadores físicos) es paralela a nuestra propia arquitectura (Axiomas + Tools). Integrar esto documenta nuestra propia auto-simetría.
```
