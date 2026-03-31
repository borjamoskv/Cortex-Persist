---
description: Ejecuta el protocolo MEMORIA para persistir el contexto de la sesión actual en CORTEX (v4 - Full Ontology)
---

# Workflow: MEMORIA (v4)

Protocolo optimizado de persistencia de contexto para CORTEX v4. Ejecuta estos pasos en orden:

// turbo-all

1. **Smart Check**: Comprueba si el snapshot global está fresco (< 1 hora).
   - Si `~/.cortex/context-snapshot.md` tiene menos de 1 hora, **recomienda al usuario saltar la ejecución completa** a menos que quiera forzar un update.
   - Comando para verificar edad:

     ```bash
     find ~/.cortex/context-snapshot.md -mmin -60 2>/dev/null
     ```

2. **Recall**: Carga el estado actual del proyecto desde CORTEX:

   ```bash
   cd ~/cortex && .venv/bin/python -m cortex.cli recall $(basename "$(pwd)") 2>/dev/null || echo "No prior context"
   ```

3. **Analyze**: Analiza la conversación actual y extrae la ontología completa de CORTEX v4:
   - **Decisions**: Decisiones de diseño o arquitectura tomadas (Reasoning required).
   - **Knowledge**: Hechos aprendidos sobre el proyecto.
   - **Errors**: Errores encontrados con CAUSA y FIX.
   - **Ghost**: Estado actual del proyecto (última tarea, estado, bloqueadores) desde `task.md`.
   - **Bridges**: Conexiones entre proyectos (Patrón, Nota).
   - **Axioms**: Verdades fundamentales del sistema.
   - **Rules**: Restricciones operativas obligatorias.
   - **Tasks**: Unidades lógicas de trabajo o gaps identificados.
   - **Schemas**: Definiciones de estructuras de datos.

4. **Store Batch**: Genera un JSON temporal con TODOS los facts y súblelos de golpe.
   - Crea un archivo `_facts.json` con una lista de objetos: `[{"project": "...", "content": "...", "fact_type": "...", "tags": ["..."]}]`
   - Ejecuta la carga batch:

     ```bash
     cd ~/cortex && .venv/bin/python -m cortex.cli store-batch _facts.json
     rm _facts.json
     ```

5. **Ghost Update**: Si hay un cambio de estado en el proyecto, actualiza el `task.md` activo para reflejar el nuevo estado (Status: active/shipping/dormant).

6. **Export**: Exporta el snapshot global actualizado:

   ```bash
   cd ~/cortex && .venv/bin/python -m cortex.cli export
   ```

7. **Notify**: Confirma al usuario con un resumen de los facts persistidos y el estado del snapshot.

---

> **Véase también:** `/recall` para cargar contexto, `/cortex-recall` para boot rápido.
