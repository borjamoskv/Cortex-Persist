<!-- [C5-REAL] Exergy-Maximized -->
# CORTEX SICA: Structural Genetic Drift & Ouroboros Convergence

> **Reality Level:** `C5-REAL`  
> **Milestone Alignment:** `death_protocol` (AI Code Hygiene & OSS Metabolism) / `cryptographic_autopoiesis_swarm_thermodynamics` (Swarm Autopoiesis)

## 0x01. Overview

To prevent premature cognitive convergence (overfitting to historical tasks) and technical stagnation in the autonomous swarm (SICA), a thermodynamic **Structural Genetic Drift** has been integrated natively into the `Heuristic` reproductive lifecycle. 

This mechanism acts as a biological metabolism for the swarm, continuously destroying rigid parameter assumptions and injecting low-level stochastic variance into the genetic transmission of reasoning components.

## 0x02. Implementation Details

The metabolism is implemented at two critical loci within the `cortex.sica.colony.genetics` substrate:

1. **Adoption Drift (`_apply_fragment`)**
   When an agent adopts a foreign heuristic from the `GenePool` (horizontal gene transfer), the structural integrity of the heuristic's weighting is deliberately weakened. There is a 20% probability that the weight parameter will drift by $\pm 10\%$ ($\delta \in [-0.1, 0.1]$).

2. **Crossover Mutation (`crossover`)**
   During sexual reproduction (merging two parental `StrategyGenome` objects), all inherited heuristics undergo systemic mutation. Every heuristic has a 15% probability of shifting its weight by $\pm 15\%$ ($\delta \in [-0.15, 0.15]$), clamped unconditionally to `[0.1, 1.0]`.

## 0x03. Thermodynamic Justification (Exergy Flow)

By preventing the weights from crystallizing eternally at optimal peaks ($w=1.0$), the swarm maintains a state of **metastability**. 

- **Entropy Injection:** The drift ensures the system never fully reaches thermodynamic equilibrium, which in optimization terms translates to escaping local minima. 
- **Ouroboros-Infinity:** Code hygiene is achieved not by deleting bad code, but by letting poor heuristics gradually drift downward in weight until they are purged by natural selection (tournament). This satisfies the `Death Protocol`, where software naturally metabolizes its own outdated logic.

*State: Forged and Crystallized. (Commit: 997624c0)*
