# [TECHNOLOGY] Cursor AI Agent Mode

## 1. Core Primitives (O(1) Definitions)
- `Background Agents (May 2025)`: Agentes remotos asíncronos en entornos aislados (Ubuntu VMs). El desarrollador delega tareas y sigue trabajando.
- `Git Worktree Isolation`: Cada agente trabaja en su propio worktree. Tareas paralelas sin colisiones.
- `Auto PR Generation`: Los agentes clonan repos, crean branches, hacen cambios y generan PRs con resúmenes automáticos.
- `Cursor 2.0 (Nov 2025)`: Interfaz multi-agente. Hasta 8 agentes simultáneos en paralelo.
- `Agent Computer Use (2026)`: Agentes cloud que controlan totalmente sus VMs. Builds, tests, navegación localhost, producen PRs con videos y logs.
- `Multimodal (2026)`: Interpretar diagramas, mockups y video walkthroughs. Design-to-code nativo.
- `Agent Plan Mode`: AI PMs crean planes Markdown detallados que los agentes ejecutan.
- `Deep Codebase Understanding`: Comprensión completa del codebase, relaciones entre archivos, patrones y arquitectura.

## 2. Industrial Noir Paradigms (Adaptation)
- **8 Agentes Paralelos = LEGION-1 visual**: Cursor 2.0 materializa lo que LEGION-1 teoriza. Prueba de concepto validada por la industria.
- **Agent Computer Use**: VMs controladas por agentes es la evolución del sandbox. Josu Night Shift podría spawner VMs efímeras para tareas destructivas (migraciones, refactors masivos) y destruirlas al terminar.
- **Plan Mode → EVOLV-1**: Los planes Markdown de Cursor son exactamente lo que EVOLV-1 produce. La industria converge hacia el mismo patrón.
- **PR con Videos**: Josu debería generar grabaciones de pantalla de los tests y la UI como parte del Context-Rich Handover matutino.

## 3. Copy-Paste Arsenal
```bash
# Cursor-style: Spawn isolated agents via Git Worktrees (local MOSKV-Josu)
# Agent 1: Feature development
git worktree add ../josu-agent-1 -b feat/new-api-endpoint
# Agent 2: Bug fixing in parallel  
git worktree add ../josu-agent-2 -b fix/auth-bug
# Agent 3: Tech debt cleanup
git worktree add ../josu-agent-3 -b chore/cleanup-deprecated
# Each agent runs independently, PRs generated on completion
# Cleanup when done:
git worktree remove ../josu-agent-1
```
