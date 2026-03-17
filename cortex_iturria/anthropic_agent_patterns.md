# [TECHNOLOGY] Anthropic Agent Patterns (Building Effective Agents)

## 1. Core Primitives (O(1) Definitions)
- `Context Engineering > Prompt Engineering`: La nueva disciplina. No es qué le dices al modelo, sino cómo configuras todo el contexto (herramientas, memoria, estado) para obtener el comportamiento deseado.
- `Simple, Composable Patterns`: Los agentes más exitosos NO dependen de frameworks complejos. Patrones simples y componibles ganan.
- `Orchestrator-Worker`: Patrón multi-agente donde un agente líder coordina sub-agentes especializados. Mejora sustancial sobre single-agent para investigación compleja.
- `Long-Running Agent Harness`: Para tareas de horas/días: un agente inicializador prepara el entorno, y un coding agent hace progreso incremental dejando artefactos claros entre sesiones.
- `Compaction + Agentic Memory`: Técnicas para gestionar la ventana de contexto finita: compactación y toma de notas estructurada para mantener coherencia.
- `Agent Skills (Open Standard)`: Paquetes modulares de capacidades basados en filesystem que los agentes descubren y cargan dinámicamente. Validation-first, progressive context loading.

## 2. Industrial Noir Paradigms (Adaptation)
- **Context Engineering = CORTEX Core**: La tesis de Anthropic valida que CORTEX no es "otra base de datos de facts", sino un motor de ingeniería de contexto. El valor está en CÓMO se inyecta el contexto, no en cuánto se almacena.
- **Compaction**: CORTEX ya implementa compactación. Anthropic confirma que es crítica para agentes de larga ejecución (como Josu Night Shift).
- **Skills = SORTU/DEMIURGE**: Los Agent Skills de Anthropic son conceptualmente idénticos al sistema de Skills de MOSKV-1 (filesystem-based, auto-descubribles).

## 3. Copy-Paste Arsenal
```python
# The Context Engineering Principle (MOSKV-1)
# Don't optimize prompts. Optimize the ENTIRE context window.
context = {
    "system": system_prompt,
    "tools": dynamically_loaded_skills,      # Agent Skills
    "memory": compacted_cortex_facts,         # Compaction
    "state": current_task_artifacts,          # Agentic Memory
    "history": last_n_turns_only              # Window management
}
# The quality of THIS dict determines agent performance.
```
