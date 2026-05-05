# Memoria Local — CORTEX Persist

Última actualización: 2026-05-05

## Convenciones activas

- Los límites "sin máximo" o no acotados deben representarse explícitamente como `None`, no como enteros centinela artificiales.
- En guardrails de agentes, `max_turns: 0` se acepta solo como alias heredado de compatibilidad y debe normalizarse internamente a `None`.
- Si un valor de límite está omitido, debe preservarse el comportamiento por defecto de esa superficie; no reinterpretar ausencia como "infinito" salvo que el contrato de esa API ya lo defina así.
- El schema YAML de agentes declarativos usa `DeclarativeAgentSpec` como nombre canónico; `AgentRole` queda solo como alias heredado de compatibilidad.
- `role.yaml` sigue siendo un nombre de fichero legacy válido para scaffolds/configs, pero no es el nombre del concepto; al documentarlo, tratarlo como convención de fichero, no como tipo.
- El `AgentRole` de `cortex/extensions/swarm/protocols.py` es un enum distinto y no debe confundirse con el schema declarativo ni con los `governance_role` definidos en `AGENTS.md`.
- El 2026-05-05 se añadió el proveedor `cortex_omega` a `config/llm_presets.json` como perfil local frontier/free `qwen-3.6-plus-omega` sobre Ollama, con `qwen2.5-coder:7b` para code/architect y `cortex-8b-solver:latest` para reasoning/general. El preset `ollama` debe usar solo modelos verificados en `ollama list`: `cortex-8b-solver:latest`, `llama3.2:latest`, `qwen2.5-coder:7b`, `glm-5.1:cloud`.
- La superficie operativa del perfil anterior vive en `cortex/extensions/llm/qwen_omega.py` y CLI `cortex qwen`: `status`, `infer`, `batch`, `validate`, `compare`. Validación acepta JSON parseable aunque `spectral_audit` lo marque corto; no implica persistencia automática ni bypass de guards.
- `cortex.extensions.adk` es la implementación canónica de ADK; `cortex.adk` debe mantenerse como superficie legacy compatible mediante shims o delegación, no como copia divergente.
