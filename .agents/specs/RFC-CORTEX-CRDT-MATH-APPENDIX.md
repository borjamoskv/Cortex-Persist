# Appendix: Cortex-Persist CRDT Merge Semantics

> **Status:** Open Formal Appendix

This document defines the formal mathematics and algebra required for Cortex-Persist Semantic Swarm Sync.

## 1. Entity CRDT Typology 
*(Pending formalization)*
- Belief Object CRDT structures
- Monotonicity requirements

## 2. Merge Semantics
*(Pending formalization)*
- Partial ordering of belief patches
- Conflict resolution algorithms beyond Last-Write-Wins (LWW)

## 3. LogOP Veto Saturation Rules
*(Pending formalization)*
- Interaction between `consensus_weight`, LogOP, and ZK proofs.
- Mathematical constraints on $P \to 0$ convergence.

## 4. Network Partitions & Tombstones
*(Pending formalization)*
- Convergence rules under partition logic.
- Treatment of suspension/discarded states as semantic tombstones.
