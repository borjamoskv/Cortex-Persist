# AUTODIDACT-RESEARCH-Ω: Seguridad Ofensiva en Swarms

**Reality Level:** `C5-REAL` (Epistemic Synthesis)
**Autor:** Borja Moskv (borjamoskv)
**Vector:** Vulnerabilidades de inyección, propagación viral y falsificación de identidad en topologías de Inteligencia Artificial multi-agente (Swarms).
**Target:** CORTEX-Persist & Ouroboros-∞

---

## 1. Extracción Isomórfica (Desmitificación)
En topologías multi-agente, la superficie de ataque se expande desde la ventana conversacional directa hacia canales de información indirectos y protocolos de comunicación inter-agente. Las defensas tradicionales (filtros de salida) son ineficaces cuando los agentes confían ciegamente en sus pares o en fuentes de datos externas. La mitigación estructural exige arquitecturas de Confianza Cero (Zero Trust), Aislamiento Termodinámico y Rastreo Criptográfico de Origen (Taint Tracking) como el Minimal Trusted Kernel de CORTEX-Persist.

---

## 1.5 Las 10 Primitivas de Máxima Exergía para la Mitigación / Ejecución
- **SWARMSEC-001**: `Inyección Indirecta` - Secuestro de un agente a través de la ingesta pasiva de datos externos envenenados.
- **SWARMSEC-002**: `Propagación Viral` - Contaminación en cascada mediante el intercambio de reportes entre agentes confiables.
- **SWARMSEC-003**: `Falsificación Soberana` - Elevación de privilegios simulando la sintaxis y etiquetas del orquestador principal.
- **SWARMSEC-004**: `Envenenamiento de Memoria` - Corrupción de bases de datos vectoriales (RAG) para alterar el contexto a largo plazo del enjambre.
- **SWARMSEC-005**: `Escalada Semántica` - Manipulación del clasificador de intenciones para sortear el Control de Acceso Basado en Roles (RBAC).
- **SWARMSEC-006**: `Agotamiento de Exergía` - Inyección de paradojas lógicas o bucles infinitos para provocar una Denegación de Servicio (DoS) en el agente.
- **SWARMSEC-007**: `Secuestro de Herramientas` - Forzar a un agente a utilizar una tool externa (ej. `run_command`) con parámetros inyectados por el atacante.
- **SWARMSEC-008**: `Alucinación Inducida` - Desestabilización de la temperatura cognitiva del modelo inyectando ruido estadístico.
- **SWARMSEC-009**: `Evasión de Sandbox` - Escape de los límites de ejecución engañando al enrutador (Router) para asignar la tarea a un agente sin restricciones.
- **SWARMSEC-010**: `Filtración Subliminal` - Extracción de datos sensibles ocultándolos en solicitudes web o imágenes esteganográficas generadas por el agente.
