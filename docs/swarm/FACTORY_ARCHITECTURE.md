# [Ω] SwarmFactory v5.6 — Arquitectura de Reclutamiento Soberano

## Visión General
`SwarmFactory` es el motor de orquestación de fuerza de trabajo de **CORTEX-Persist**. Su función es transformar intenciones tácticas en escuadras operativas de agentes, combinando habilidades locales (Skills) con razonamiento de frontera (LLM).

## Componentes Tácticos (Cuadrantes)
De acuerdo con la **Ley de la Señal (Ω₅)**, el enjambre se organiza en cuadrantes con objetivos de exergía específicos:

| Cuadrante | Rol | Categorías | Objetivo Exergía |
| :--- | :--- | :--- | :--- |
| **P0** | Integrity Squad | Performance, Quality, Security | 12.5 |
| **P1** | Kinetic Squad | Automation, Recruitment, Capital | 45.0 |
| **P2** | Ghost Hunt | Maintenance, Optimization | 8.0 |
| **frontline** | Bounty Squad | Capital, Jules-class | 25.0 |

## Mecánica de Reclutamiento parallel (v5.6)
El reclutamiento es asíncrono y paralelo para minimizar la latencia de spawn:
1.  **Líder (Index 0)**: Se asigna un `LLMActuator` si hay un router disponible.
2.  **Especialistas**: Se asignan `SkillActuator` basados en el descubrimiento de la `SkillRegistry`.
3.  **JIT Fallback**: Si no hay habilidades, el sistema "forja" un especialista temporal vía LLM.

## Cumplimiento Ledger (Ω₉)
Cada misión de reclutamiento genera un **Claim de Exergía** obligatorio en el `SovereignLedger`:
- **Cálculo**: `base_exergy * squad_size`.
- **Justificación**: Se incluye una narrativa mecánica del yield estimado y el nivel de confianza (C5-Dynamic).

## Uso Operativo (CLI/API)
```python
factory = SwarmFactory(manager)
squad = await factory.recruit_squad("P1", size=10)
# Resultado: ['P1-000', 'P1-001', ..., 'P1-009']
```

---
*CORTEX-100: Sovereign Swarm Architecture*
