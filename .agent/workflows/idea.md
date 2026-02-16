---
description: Genera 3 caminos divergentes para resolver un problema usando el contexto de CORTEX.
---

# Workflow: IDEA

Este workflow utiliza el contexto del proyecto y la capacidad de razonamiento del modelo para generar soluciones creativas y divergentes.

// turbo-all

1. **Context Load**: Carga el contexto relevante del proyecto actual.
   ```bash
   basename "$(pwd)"
   cd ~/cortex && .venv/bin/python -m cortex.cli recall $(basename "$(pwd)") 2>/dev/null
   ```

2. **Input**:
   - Solicita al usuario el problema, tópico o funcionalidad sobre la que desea idear.
   - Si el usuario ya lo proporcionó en el prompt inicial, úsalo directamente.

3. **Divergent Generation**:
   Genera 3 enfoques distintos y preséntalos en una tabla o lista comparativa:

   | Enfoque | Filosofía | Pros | Contras |
   | :--- | :--- | :--- | :--- |
   | **🛡️ Safe** | La solución estándar, robusta y "aburrida". Best practices. | Fiable, rápido de implementar. | Poco innovador. |
   | **🧪 Experimental** | Probando tecnologías nuevas, betas o enfoques no tradicionales. | Innovador, aprendizaje alto. | Riesgo de bugs, curva de aprendizaje. |
   | **🌌 Galaxy Brain** | Pensamiento lateral extremo. Reescribir las reglas. "Over-engineering" con propósito. | Potencialmente revolucionario. | Alto riesgo, puede ser overkill. |

4. **Selection**:
   Pregunta al usuario cuál de los enfoques prefiere explorar o si quiere una mezcla.

5. **Persistence**:
   Una vez seleccionada una dirección (o una idea específica), guárdala en CORTEX:
   ```bash
   cd ~/cortex && .venv/bin/python -m cortex.cli store "<PROJECT>" "Idea: <RESUMEN_IDEA>" --type knowledge --tags "idea, planning, <ENFOQUE>"
   ```
