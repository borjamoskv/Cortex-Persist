# Curso · Optimización de LLMs y Agentes IA

## Objetivo

Estudiar la optimización como problema de sistema: complejidad, puertas de calidad, control de entropía y feedback operativo.

## Anclas del repo

- [Entropy gate](../../../scripts/entropy_gate.py)
- [Ship gate](../../../scripts/ship_gate.py)
- [Swarm dashboard](../../../scripts/swarm_dashboard.py)
- [Guardrails de sesión](../../../cortex/memory/guardrails.py)
- [Tests del supervisor](../../../tests/agents/test_builtin_agents.py)

## Qué aprendes

- Por qué optimizar no es solo bajar latencia o coste.
- Cómo complejidad, lint, tests y gates modelan la calidad del agente.
- Cómo distinguir “más rápido” de “seguro para enviar”.
- Por qué optimizar sin guardrails observables degrada la confianza.

## Labs

- Escribe una nota corta: benchmark frente a ship gate.
- Identifica una optimización que reduzca coste pero aumente riesgo de confianza.
- Diseña un scorecard mínimo de optimización para este repo.

## Criterio de salida

Puedes defender una optimización con evidencia de ingeniería y no con promesas vagas.
