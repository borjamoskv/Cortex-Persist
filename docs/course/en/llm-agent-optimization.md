# Course · LLM and AI Agent Optimization

## Goal

Study optimization as a systems problem: complexity ceilings, ship gates, entropy control, and operator feedback loops.

## Repo Anchors

- [Entropy gate](../../../scripts/entropy_gate.py)
- [Ship gate](../../../scripts/ship_gate.py)
- [Swarm dashboard](../../../scripts/swarm_dashboard.py)
- [Session guardrails](../../../cortex/memory/guardrails.py)
- [Supervisor tests](../../../tests/agents/test_builtin_agents.py)

## What You Learn

- Why optimization is not only about latency or cost.
- How complexity, linting, tests, and gates shape agent quality.
- How to distinguish “faster” from “safe to ship”.
- Why optimization without observable guardrails erodes trust.

## Labs

- Write a short memo: benchmark vs ship gate.
- Identify one optimization that lowers cost but raises trust risk.
- Design a minimal scorecard for LLM and agent optimization in this repo.

## Exit Criteria

You can argue for an optimization change with engineering evidence instead of vague model claims.
