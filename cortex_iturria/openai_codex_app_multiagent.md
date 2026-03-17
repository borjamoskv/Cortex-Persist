# [TECHNOLOGY] OpenAI Codex App: Multi-Agent Architecture

## 1. Core Primitives (O(1) Definitions)
- `Multi-Agent Orchestration`: El "Codex App" actúa como Command Center. Permite correr múltiples agentes en paralelo organizados en threads aislados que no pierden histórico de contexto.
- `Git Worktree Isolation`: Cada agente trabaja sobre su propia copia aislada del código fuente usando Git worktrees para evitar colisiones durante la experimentación concurrente.
- `Agent Skills`: Workflows empaquetados (prompts + scripts + APIs). Extienden Codex más allá del código crudo (ej. automatizando Figma-to-UI, o despliegues Cloudflare/Vercel).
- `Automations / TUI`: Ejecución programada o periódica de agentes ("cron-agents") para tareas repetitivas. Además, el CLI de Codex introduce TUI avanzado con sintaxis coloreada, atajos de voz y manejo fluido de contexto en terminal.

## 2. Industrial Noir Paradigms (Adaptation)
- **Git Worktree Isolation**: Paradigma de adopción obligatoria para *LEGION-1*, *BERRERAIKI* y *SYNTHESIS-OMEGA*. Al spawnear sub-agentes para exploración o refactorización masiva, usar worktrees en lugar de ramas directas protege el "master state" y previene merge hells destructivos durante la ideación A/B.
- **Skill Forging Equivalency**: La adopción de la librería de Skills por OpenAI reafirma la visión base de MOSKV-1 (*SORTU* / *DEMIURGE-OMEGA*): los agentes no necesitan solo promts, necesitan APIs de sistema operátivo. Los skills deben tratarse como primitivas instalables en repos.
- **Automations as Cron-Agents**: Abre la puerta a desacoplar chequeos pesados (limpieza, refactorización de tech debt con *SUNTSITU*) hacia cron-jobs manejados por *RADAR-OMEGA* asíncronamente.

## 3. Copy-Paste Arsenal
*Nota: Aislamiento físico de la Legión AI mediante Git Worktrees.*

```bash
# O(1) Branching for parallel Agent Swarm execution without touching CWD
# When orchestrating multiple agents, give each its own physical workspace.
git worktree add ../cortex_agent_experiment_omega -b feat/agent-exploration-omega
cd ../cortex_agent_experiment_omega
# -> LEGION-1 executes here safely.
# -> Review diff visually.
# -> Merge or discard.
git worktree remove ../cortex_agent_experiment_omega
```
