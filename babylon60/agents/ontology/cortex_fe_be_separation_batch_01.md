# ONTOLOGY-FORGE-OMEGA: FRONTEND / BACKEND SEPARATION & AGENT BOUNDARIES (BATCH 1)
**Dominio:** Separación FE/BE, Skills, Projects, Mission Control y ParseToolArgs en C5-REAL
**Sys_ID:** `borjamoskv` | **Estado:** C5-REAL
**Autor:** Borja Moskv

## MATRIZ 1: 5 PRIMITIVAS DE COLAPSO (FBE-P01..05)
Mecanismos elementales de fallo de límites, fugas de contexto y desalineación FE/BE.

| ID | Primitiva | Mecanismo Causal | Activación (Trigger) | Sensor (Síntoma) | Escala Temporal | Gravedad | Intervención |
|:---|:---|:---|:---|:---|:---|:---|:---|
| **FBE-P01** | `OP_CONTEXT_OVERLOAD` | Sobrecarga de la ventana de contexto del agente debido a la ingesta masiva de reglas sin modularización. | Carga estática de todas las directivas de UI y backend en el System Prompt. | Caída brusca en precisión AST / Olvido de invariantes de base de datos. | Lenta | P1 | Implementar carga dinámica de **Skills** bajo demanda (divulgación progresiva). |
| **FBE-P02** | `OP_PAGEID_LEAK` | Exposición de identificadores de sesión de navegador `PageID` en contextos de backend inseguros. | Almacenamiento de `PageID` en tablas de hechos persistentes sin firma. | `PageID` visible en logs crudos o respuestas API no encriptadas. | MS | P0 | Segregación de ParseToolArgs visuales y encriptación de identificadores temporales. |
| **FBE-P03** | `OP_CROSS_PROJECT_MUTATION` | Modificación de archivos fuera de la carpeta/repositorio asignados al agente. | Herramientas de filesystem llamadas con rutas relativas que escapan al `Project` actual. | Modificación accidental de archivos en `/System` o repositorios adyacentes. | Segundos | P0 | Validación de sandbox de rutas absolutas basada en `Project` boundaries. |
| **FBE-P04** | `OP_UNRESTRICTED_PARSET_ARGS` | Ejecución de operaciones destructivas en el backend con tipado de frontend. | Paso de argumentos estocásticos a través de structs de ejecución de herramientas. | Error de tipado AST o ejecución inesperada en comandos de terminal. | MS | P1 | Forzar esquemas estrictos de ParseToolArgs para herramientas de ejecución. |
| **FBE-P05** | `OP_MISSION_CONTROL_DESYNC` | Pérdida de traza de ejecución cruzada entre agentes especializados en frontend y backend. | Delegación directa de tareas entre agentes sin pasar por el bus central supervisado. | Huérfanos en la secuencia de eventos del Ledger / Inconsistencia de estado. | Segundos | P0 | Canalizar toda delegación a través del enrutador de **Mission Control**. |

## MATRIZ 2: 5 INVARIANTES TERMODINÁMICAS (FBE-I01..05)
Leyes del aislamiento de límites y control de exergía en entornos distribuidos.

| ID | Invariante | Lógica / Principio | Implicación Operacional | Condición de Borde | Métrica Falsable |
|:---|:---|:---|:---|:---|:---|
| **FBE-I01** | `INV_SKILL_PROGRESSIVE` | Los conocimientos específicos de entorno se estructuran en Skills que permanecen inactivos hasta ser invocados. | Evita la degradación del rendimiento por Context Rot (Ω₂). | Carga de prompt en el runtime del agente. | `loaded_skills_context_size <= 2048 bytes`. |
| **FBE-I02** | `INV_PROJECT_BOUNDS` | Todo agente opera confinado a los límites físicos y lógicos de su Project asignado. | Previene la contaminación y mutaciones cruzadas de código. | Operación de escritura en sistema de archivos. | `file_path.is_relative_to(project.root) == True`. |
| **FBE-I03** | `INV_PARSET_SEPARATION` | Las herramientas diferencian estrictamente entre control de interfaz (PageID) y lógica interna. | Evita mezclar flujos síncronos de navegador con hilos de ejecución de backend. | Construcción de ParseToolArgs. | `isinstance(args, BrowserArgs) != isinstance(args, CodeArgs)`. |
| **FBE-I04** | `INV_MISSION_AUDIT` | Toda transacción multi-proyecto es orquestada y registrada por Mission Control en el Ledger. | Mantiene la auditabilidad forense inmutable de los flujos de trabajo cross-project. | Mutación de estado multi-proyecto. | `ledger.contains_transaction(mission_id) == True`. |
| **FBE-I05** | `INV_TAINT_ISOLATION` | Los datos procedentes del renderizado visual de front-end se marcan con un taint flag de UI. | Evita que datos estocásticos no validados contaminen la capa de persistencia crítica. | Inserción de hechos del navegador. | `fact.metadata.get("ui_taint") == True`. |

## MATRIZ 3: 3 ANTIPATRONES ESTOCÁSTICOS (FBE-AP01..03)
Fragilidades arquitectónicas en el manejo de límites de agentes.

| ID | Antipatrón | Disfunción Causal | Señal de Presencia | Impacto en Robustez | Refactor (Alternativa) |
|:---|:---|:---|:---|:---|:---|
| **FBE-AP01** | **Context Mono-Agent** | Inyectar todas las capacidades y guías en un único super-agente monolítico. | Prompt de sistema que supera las 2000 líneas con guías FE y BE mezcladas. | Alta entropía en la selección de herramientas y baja precisión. | Segregar en agentes especializados e importar **Skills** bajo demanda. |
| **FBE-AP02** | **Project Escapist** | Permitir que las herramientas de ejecución de comandos se ejecuten en cualquier directorio sin anclaje en el Project. | `Cwd` ausente o no validado en llamadas a comandos de consola. | Modificación de configuraciones globales del sistema operativo. | Enforce de `project_root` dinámico en `ToolRegistry` y sandbox. |
| **FBE-AP03** | **Stochastic UI Injection** | Persistir respuestas directas del navegador (ej. web scraping) en el backend sin filtrado tipado. | Ingesta de HTML/Text raw sin transformación de ParseToolArgs. | Envenenamiento de embeddings y pérdida de integridad en el vector store. | Filtrado por ParseToolArgs estructurados en el paso de validación SAGA. |
