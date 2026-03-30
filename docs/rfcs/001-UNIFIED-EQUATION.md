# RFC-001: The CORTEX Unified Equation (v0.1)

> **Status:** IMPLEMENTATION PHASE
> **Target:** `cortex/engine/exergy_mixin.py`, `cortex/ledger.py`, `tests/test_unified_equation.py`
> **Author:** CORTEX Sovereign Singularity

## 1. Abstract
The Unified Equation bounds generative stochasticity (LLMs) with formal thermodynamic constraints. It integrates Rate-Distortion (compression), Bayesian crystallization (the Ledger), and POMDP (execution under uncertainty) into a single deterministic gate: The Promotion Gate. Only causal sequences yielding positive Net Exergy ($\Delta\Xi > 0$) are persisted.

## 2. Theoretical Invariants

$$ \max_{A} \mathbb{E}[\Xi(s, A)] \quad \text{s.t.} \quad I(S; O) \le R_c $$

- **Rate-Distortion Collapse:** $B_t \rightarrow B_t^*$. Minimizing uninformative thermal noise (entropy) while bounding semantic divergence ($D \le \epsilon$).
- **Epistemic Crystallization:** $B_t^* \rightarrow \Delta L_t$. Output must clear deterministic guards to become irreversible ledger truth.
- **Sovereign POMDP:** Agent selects actions maximizing compound exergy over finite windows.

## 3. The Exergy Formula (v3.0)

Exergy ($\Xi$) is the proxy for "executable useful truth".

$$ \Xi_t = (\Delta C_{gap} \cdot \omega) - (E_{inj} \cdot \lambda_{cost}) $$

Where:
- $\Delta C_{gap}$: Reduction in algorithmic uncertainty (tests passed, axioms validated, dependencies resolved).
- $\omega$: Operational weight (task criticality).
- $E_{inj}$: Entropy injected into the system (LLM sampling temperature, total tokens burned, context window complexity).
- $\lambda_{cost}$: The physical toll (latency, hardware deprecation limit).

## 4. Solid State Trigger

The transition to SOLID STATE occurs when:
1. `entropy_injection` < `dissipation_capacity`
2. `exergy_gradient` ($\frac{d\Xi}{dt}$) > $0$
3. `causal_integrity` == `True` (Acyclic, verified, ledger-backed graph).

## 5. Architectural Map

1. **`cortex/engine/exergy_mixin.py`**: The calculable measurement of $\Xi_t$.
2. **`cortex/ledger.py`**: Expanding index structures to prune ghosts and enforce deterministic invalidation of $L_t$.
3. **`cortex/guards/promotion_gate.py`**: The ultimate barrier. Discards $B_t^*$ if $\Xi_t \le \Xi_{threshold}$.

## 6. Edge Cases Handled
- **Silent Collapse**: Blocked via `contradiction_guard` + cross-ledger validation.
- **Ghost Explosion**: Solved by garbage-collecting embeddings devoid of active ledger commitments.
- **Over-crystallization**: Mitigated by controlled entropy scaling (`temperature = 0.3 + U(0.1, 0.2)` on stagnation).
- **Evolutionary Degeneration**: Novelty search integrated into $\Xi$ evaluation.
