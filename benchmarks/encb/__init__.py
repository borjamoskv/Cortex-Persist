"""ENCB v2 — Epistemic Noise Chaos Benchmark.

Self-contained benchmark framework for empirically falsifying the
Cortex-Persist cognitive hypervisor hypothesis under structured
epistemic noise. No CortexEngine dependency at runtime.

Modules:
    belief_object  — Typed BeliefObject (Boolean/Categorical/Scalar/Set)
    merge          — CRDT merge operators per belief type
    logop          — Log-odds pooling with reliability weighting
    atms           — ATMS-lite assumption tracking & invalidation
    agents         — NodeProfile + 5 adversary archetypes
    universe       — Proposition universe generator
    strategies     — S0 (LWW), S1 (RAG), S2 (CRDT-only), S3 (Cortex)
    metrics        — PFBR, TER, EDI, CNCL formal implementations
    runner         — Monte Carlo simulation runner
    ablations      — Ablation variants of S3
    plots          — Matplotlib/seaborn visualizations
"""

__version__ = "2.0.0"
