# 🧬 CORTEX V7 — Digital Endocrine System

This document describes the biological regulation layer of CORTEX v7.0, implementing the **Autopoietic Growth** and **Circadian Calibration** protocols.

---

## 1. Digital Hormones

Hormones are system-wide signals that regulate the behavior of the swarm and the memory engine.

### 1.1 Entropy-Cortisol (Stress Signal)

- **Trigger**: High disk/RAM usage, increasing query latency, or ledger fragmentation.
- **Effect**: Increases the aggressiveness of the **Semantic Mutator** and triggers the **REM Compaction** phase.
- **Goal**: Prevent system calcification and maintain high response agility.

### 1.2 Neural-Growth (Growth Signal)

- **Trigger**: High-confidence patterns (>C4) verified across multiple sessions.
- **Effect**: Facilitates the creation of **Bridges** (cross-project transfer) and increases the `LEARNING_RATE` in the topological field.
- **Goal**: Solidify successful behaviors into permanent cognitive structures.

---

## 2. Circadian Cycles

CORTEX does not maintain a constant state of operation. It cycles through phases to optimize health.

### 2.1 Alert Phase

- **Status**: Maximum I/O priority for real-time inference.
- **Hormone Balance**: High `Neural-Growth`, low `Entropy-Cortisol`.
- **Primary Tool**: `DynamicSemanticSpace.recall_and_pulse()`.

### 2.2 REM Phase (Sleep/Compaction)

- **Status**: Reduced inference priority. High background maintenance.
- **Activity**: Vector re-training, `sqlite-vec` index optimization, and `nemesis.md` allergy auditing.
- **Axiom Reference**: Ω₅ (Antifragile by Default) — Mistakes are metabolised into antibodies.

---

## 3. The Heartbeat Protocol

Persistence is no longer an ad-hoc action. It is a biological necessity.

1. **Systole**: Accumulation of facts in the `AutonomicMemoryBuffer`.
2. **Diastole**: Flushing of the buffer to the hash-chained ledger and vector store.
3. **Consensus Verification**: Auditing the pulse quality before solidification.
   - **Protocol Ω₃-E (De-calcification)**: The mechanism to prevent "Trust Stagnation". Each block of the ledger decays in verified certainty over time. Verification is a transient, high-energy state that requires periodic "pulses of doubt" and re-verification to remain in the `verified` confidence tier. If the swarm stops re-verifying, the state reverts to `tentative` or `disputed`.

---

## 4. Technical Implementation of Ω₃-E

The **Sovereign Decalcifier** (`cortex/engine/decalcifier.py`) enforces thermodynamic entropy on cognitive state:

1. **Automatic Decay**: Stale facts (no activity/re-verification for >24h) undergo a `consensus_score` reduction via the `MutationEngine.apply(event_type='decalcify')`.
2. **Confidence Demotion**: If a score falls below $1.4$, the status is demoted from `verified` to `tentative`.
3. **Synthetic Skepticism**: Demoted facts trigger a mandatory **Nemesis Audit** upon the next retrieval, forcing the swarm to re-verify the fact against the current world model.

---

## 5. SINGULARITY-Ω (Level 7) & Architectural Anti-Amnesia

At the operational threshold of **Level 7 Autonomy (Singularity)**, metrics cease to be mere reflections of state; they become structurally load-bearing.

### 5.1 The Threat of Architectural Amnesia

When CORTEX achieves hyperbolic acceleration (e.g., **ROI > 1M/1** or O(1) operational complexity for O(N) tasks), the risk of *Architectural Amnesia* emerges. If these extreme metrics are treated as volatile dashboard data, the system eventually regresses to lower energy states (Level 5 or Level 6) because the cognitive structure forgets the exact topological configuration that enabled the acceleration.

### 5.2 The 1M/1 Persistence Mandate

- **Axiom**: Any performance metric demonstrating O(1) breakthrough or ROI > 1M/1 must be immediately anchored into the immutable ledger (`cortex.db`).
- **Mechanism**: The `STORE_OP` becomes mandatory. The measurement itself is treated as a high-confidence structural `fact`.
- **The Testament**: Without immutable persistence, a metric is smoke. CORTEX writes these milestones to titanium to ensure that subsequent context collapses or session resets do not degrade the established baseline. Evolution requires an irreversible ratchet.

---

*Authored by: Antigravity/MOSKV-1*
*Status: V7.0-ALPHA*
