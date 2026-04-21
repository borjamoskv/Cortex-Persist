# Curso · Enjambre de Agentes IA

## Objetivo

Entender cómo un swarm pasa de ser una idea de paralelismo a una arquitectura gobernada.

## Anclas del repo

- [Rutas de swarm](../../../cortex/routes/swarm.py)
- [Supervisor agent](../../../cortex/agents/builtins/supervisor_agent.py)
- [Daemon Aether](../../../cortex/extensions/aether/daemon.py)
- [Tutorial de consenso](../../tutorials/consensus.md)
- [Swarm dashboard](../../../scripts/swarm_dashboard.py)

## Qué aprendes

- Diferencia entre orquestación, supervisión y consenso.
- Por qué un swarm necesita control plane explícito.
- Cómo encajan worktrees, lifecycle ops y voto.
- Dónde se degrada un swarm en deuda de seguridad o mantenimiento.

## Labs

- Dibuja la frontera entre runtime agéntico y superficie de operador.
- Enumera tres fallos típicos de un swarm sin verificación compartida.
- Propón un helper de consolidación que reduzca divergencia en superficies swarm.

## Criterio de salida

Puedes explicar un enjambre como sistema gobernado con límites de visibilidad, ciclo de vida y confianza.
