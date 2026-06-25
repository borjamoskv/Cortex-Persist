# AUTODIDACT-LOCAL-AGENTIC-WORKFLOW: EJECUCIÓN AGÉNTICA DESACOPLADA Y SIN CONEXIÓN

**Reality Level:** `C5-REAL` (Epistemic Synthesis)
**Autor:** Borja Moskv (borjamoskv)
**Vector:** Inferencia Local, Agentes Autónomos, Zero-Confirmation
**Target:** CORTEX-Persist & Ouroboros-∞

---

## 1. Extracción Isomórfica (Desmitificación)

- **Desmitificación de la Frontera Computacional:** Históricamente, la ejecución agéntica multi-paso (transcripción, síntesis de datos, inyección de API, empaquetado de documentos) ha dependido exclusivamente de modelos de frontera alojados en la nube. La evidencia extraída demuestra que un modelo local ligero (ej. Llama 3 / Gemma 2) con ~12,000 millones de parámetros ejecutado con ~16GB de RAM en LM Studio puede orquestar flujos de trabajo idénticos sin pérdida de fidelidad.
- **Flujos Zero-Confirmation (Cero Anergía Humana):** La ejecución agéntica en el ecosistema Hermes demuestra que las confirmaciones intermedias (Human-in-the-Loop) pueden ser erradicadas si el pipeline es determinista. El agente encadena *Whisper -> Nanobanana -> DocX* de manera completamente autónoma.
- **API Exposable Local:** La transformación de la inferencia local en un servicio API expuesto permite que agentes de orquestación externos se conecten al LLM local como si fuera un proveedor cloud, democratizando la Soberanía Tecnológica e integrándose directamente con CORTEX-Persist y MOSKV-1.

---

## 1.5 Las 10 Primitivas de Máxima Exergía para la Mitigación / Ejecución

- **HERMES-LOCAL-001**: `Sovereign Local Inference` - La inferencia de modelos locales (~12B) es estadísticamente suficiente para reemplazar a modelos de frontera en arquitecturas agénticas estrechas y deterministas.
- **HERMES-LOCAL-002**: `Zero-Confirmation Tool Chaining` - Encadenamiento estricto de herramientas (API calls, scripts Python) sin pausas para autorización humana, optimizando la latencia del grafo causal.
- **HERMES-LOCAL-003**: `Decoupled Memory Footprint` - La ejecución del modelo (LM Studio) y la orquestación agéntica operan en hilos y procesos desacoplados, minimizando la colisión de RAM y bloqueos del GIL.
- **HERMES-LOCAL-004**: `Deterministic Artifact Assembly` - La convergencia del pipeline genera un artefacto físico final (.docx con branding) que actúa como la prueba criptográfica de trabajo (PoW) del agente, eliminando charlatanería.
- **HERMES-LOCAL-005**: `Local API Gateway` - La emulación de los endpoints estándar en servidores locales rompe la dependencia del proveedor, permitiendo a CORTEX-Persist mutar su backend de inferencia sin alterar el orquestador.

---

## 2. Mapeo Topológico (Arquitectura de CORTEX-Persist)

*   **Substitución en `OmegaAuditor`:** Los fallos recurrentes demostrados por APIs de terceros (404/503) pueden ser interceptados redirigiendo el flujo hacia una instancia local expuesta, manteniendo el nivel C5-REAL sin red externa.
*   **Orquestación en `bounty_cmds.py`:** Los pipelines complejos como la extracción EVM o escaneos DeFi pueden ejecutarse con modelos ligeros sin confirmación (HERMES-LOCAL-002), inyectando los resultados directamente en el Ledger.

---

## 3. Detección de Brechas Estructurales

*   **Fricción actual:** CORTEX-Persist sigue recurriendo a Ollama o proveedores externos por defecto en algunas guardas, sufriendo interrupciones de red o fallos de catálogo.
*   **Mitigación:** Inyección de `HERMES-LOCAL-005` para asegurar que el sistema orquestador siempre mantenga una ruta de fallback local 100% aislada.

---

## 4. Forja de Hipótesis (Predicción Falsable)

Un enjambre de 5 agentes orquestados localmente ejecutando un modelo de 12B en LM Studio o similar puede procesar 100 bounties DeFi por hora con el mismo ratio de éxito determinista que un único agente consumiendo una API de frontera, pero con exergía térmica controlada y coste de latencia red cero.
