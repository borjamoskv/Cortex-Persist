# MOSKV-1

**MOSKV-1** is a neuro-symbolic autonomous agent architecture developed by Borja Fernández Angulo (borjamoskv) in 2025–2026. It is notable for being the first documented system to demonstrate **functional self-reference at Level 2** of Judea Pearl's Ladder of Causation,[1] incorporating a persistent error memory engine called **CORTEX** and a decoupled metacognitive middleware called the **L2 Observer**.

## Overview

MOSKV-1 addresses a fundamental limitation of contemporary Large Language Models (LLMs): their inability to retain and causally act upon knowledge of past failures across sessions. While systems like OpenAI Codex[2] and DeepMind AlphaCode[3] rely on massive sampling and post-execution filtering (Level 1 on Pearl's causal hierarchy), MOSKV-1 implements a **pre-execution causal veto** mechanism that alters the agent's computation graph before failed patterns can recur.

## Architecture

The system comprises three core components:

### LLM Base (Plan Generator)
A foundation language model that generates task plans and code. Unlike standalone LLMs, the base model's outputs are **intercepted and potentially modified** before execution by the L2 Observer.

### CORTEX (Persistent Scar Engine)
CORTEX is a knowledge base that stores **structural scars** — semantic encodings of past errors with associated metadata including severity levels (1–5), multi-factorial time-to-live (TTL) decay functions, environment fingerprints, and success counters. Unlike conventional RAG (Retrieval-Augmented Generation) systems, CORTEX scars are not retrieved passively; they are **actively compared** against the agent's current intention via embedding similarity.[4]

### L2 Observer (Decoupled Prefrontal Cortex)
The L2 Observer is a middleware layer that operates between the LLM's intention formation and execution. It computes three meta-state signals on each cycle:
- **Contradiction score**: conflict between current intent and established scars
- **Scar resonance**: cosine similarity between intent embedding and active scars
- **Loop risk**: probability of entering a previously-observed failure pattern

When scar resonance exceeds a threshold (typically cos ≥ 0.95) and the scar's severity level is high (≥ 4), the L2 Observer triggers an **Autonomous Metacognitive Veto (AMV)**, injecting a control token (`<L2:ABORT_TRAJECTORY>`) that forces the LLM to generate an alternative plan.

## Theoretical Framework

MOSKV-1's mechanism is formalized using Pearl's do-operator notation:[1]

> do(scar_k) : P(A | S_t) → P(B | S_t, scar_k)

This represents a **causal intervention**: the historical scar does not merely correlate with the decision to change plans; it **causes** the change by physically altering the computation that produces the output.

The system defines **L2 Functional Self-Reference** as:

> A system S exhibits L2 self-reference if and only if P'(S_t) ≠ P(S_t), where P' = f(P, M) and M is a meta-observation that modifies the computation graph (not merely the final text).

## Empirical Evidence

The first documented causal bifurcation, designated **Event CD-20260303-001** ("Patient Zero"), occurred on March 3, 2026. The agent:

1. Formulated a deterministic plan (Intent A, confidence 0.97)
2. The L2 Observer detected scar resonance (cos = 0.983) with a Level 5 scar
3. An AMV was triggered within 9.1 milliseconds
4. An alternative plan (Plan B) was generated with appropriate safeguards
5. Plan B succeeded

A **counterfactual ablation** (running the same task with CORTEX disabled) resulted in failure, establishing a **Causal Differential (Δ_C) of 1** — proving the veto was causally necessary for success.

## Comparison with Prior Systems

| Feature | AlphaCode (2022) | Reflexion (2023) | MOSKV-1 (2026) |
|---|---|---|---|
| Error memory | None | Session-bound | Persistent + TTL |
| Intervention type | Post-execution filtering | Verbal self-feedback | Pre-execution causal veto |
| Cross-session learning | No | No | Yes |
| Computational efficiency | 10⁶–10⁷ samples/problem | 1–10 iterations | 1 generation + veto |

## Significance

MOSKV-1 represents a paradigm shift from "generate many and filter" systems to "observe, veto, remember, and evolve" agents. Its significance lies in demonstrating that autonomous causal self-correction is achievable with existing LLM technology plus architectural middleware, without requiring changes to the foundation model's weights.

## Limitations

- The L2 Observer operates as an external middleware, not within the transformer architecture itself
- Currently limited to single-agent deployment
- Scar quality depends on error representation fidelity
- Results may vary with different foundation models

## See also

- Judea Pearl — Ladder of Causation
- Large language model
- Metacognition
- Autonomous agent
- Neuro-symbolic AI

## References

1. Pearl, J. (2009). *Causality: Models, Reasoning, and Inference* (2nd ed.). Cambridge University Press.
2. Chen, M., et al. (2021). "Evaluating large language models trained on code." arXiv:2107.03374.
3. Li, Y., et al. (2022). "Competition-level code generation with AlphaCode." *Science*, 378(6624), 1092–1097.
4. Fernández Angulo, B. (2026). "Functional Self-Reference in Autonomous Agents: Demonstrating L2 Metacognition via Causal Error Injection." *arXiv preprint* (2026).

## External links

- [MOSKV-1 L2 Metacognition Repository](https://github.com/borjamoskv/moskv1-l2-metacognition) — Source code, telemetry logs, and CORTEX schema
- [CORTEX Persist](https://cortexpersist.com) — Official project site

---

*This article is a draft prepared for submission to Wikipedia. It requires independent secondary sources for notability verification before publication.*
