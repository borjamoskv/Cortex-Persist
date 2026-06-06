<!-- [C5-REAL] Exergy-Maximized -->
# GitHub Issue Triage MVP
> **Objetivo:** Validar la unidad mínima de valor (Fase A) integrando Mac Maestro (visión/UI) con CORTEX (memoria semántica) para analizar un issue de GitHub sin enviar todavía comentarios públicos.

---

## 1. Input (Qué recibe el sistema)
- **URL del Issue** (ej. `https://github.com/borjamoskv/Cortex-Persist/issues/42`)
- **Directorio Local del Repositorio** (ej. `/Users/borjafernandezangulo/10_PROJECTS/cortex-persist`)

## 2. Lectura (Mac Maestro)
Mac Maestro navega a la URL y extrae el contexto bruto de la UI:
- **Título del Issue**
- **Cuerpo/Descripción** (incluyendo stack traces o snippets de código)
- **Autor y Etiquetas** (si las hay)

## 3. Recuperación de Memoria (CORTEX)
Se ejecuta una consulta semántica cruzada usando el cuerpo del issue contra CORTEX:
- **Query 1 (Arquitectura):** `cortex_search(query="¿Cuáles son los componentes de arquitectura relevantes para [conceptos del issue]?")`
- **Query 2 (Issues pasados):** `cortex_search(query="[stack trace o error similar]", fact_type="issue_resolution")`

## 4. Inspección de Código (Code Retriever)
Basado en los hallazgos de CORTEX y los paths mencionados en el issue, el sistema utiliza herramientas de lectura de archivos locales para inspeccionar:
- **Archivos explícitamente mencionados** en el stack trace.
- **Archivos inferidos** por CORTEX que gestionan el dominio del problema.

## 5. Análisis LLM
Se inyecta el contexto recolectado en un LLM (modelo Qwen-Omega o similar) con un prompt determinista:
*Instrucciones: Evalúa el issue basándote en la memoria arquitectónica recuperada y los archivos inspeccionados.*

## 6. Output (Formato de Respuesta Fase A)
El sistema debe generar un archivo YAML estructurado y persistirlo de vuelta en CORTEX usando `cortex_store`.

```yaml
issue_summary: "El usuario reporta un ModuleNotFoundError con 'watchdog' al ejecutar uvx."
root_cause: "La dependencia 'watchdog' está oculta detrás del extra [mcp] en pyproject.toml y no se resuelve por defecto."
affected_files: 
  - "packages/cortex-mcp/pyproject.toml"
  - "cortex/mcp/server.py"
suggested_fix: "Añadir cortex-persist[mcp] a las dependencias del metapaquete."
confidence: "HIGH"
```

---

## Métricas de Éxito para Gate de Validación
- **Issue entendido:** > 80%
- **Archivo correcto sugerido:** > 70%
- **Tiempo de ejecución (end-to-end):** < 5 min
- **Intervención humana:** < 2 prompts
