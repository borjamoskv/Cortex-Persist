# Multi-Agent Consensus Protocols
*Document version: 1.0.0 (Execution Level: C5-REAL) — Core Systems Group — Author: **Borja Moskv***

---

## 1. Introduction to the Consensus Substrate

To maintain Byzantine Fault Tolerance (BFT) across multi-agent swarms without relying on a centralized coordinator, CORTEX-Persist implements a layered consensus substrate. This substrate guarantees that fact injections, state transitions, and execution outcomes are validated by a supermajority of agents before being committed to the immutable Ledger.

The three core layers are:
1. **WBFT** (Weighted Byzantine Fault Tolerance) — Model response filtering.
2. **RWA-BFT** (Reputation-Weighted Asynchronous BFT) — State mutation quorum agreement.
3. **GEACL** (Gossip-Enabled Async Consensus Ledger) — P2P synchronization and coordination.

---

## 2. WBFT: Weighted Byzantine Fault Tolerance

Implemented in [`cortex/consensus/byzantine.py`](file://~/30_CORTEX/cortex/consensus/byzantine.py), WBFT assesses and filters $N$ parallel responses from LLM or subagent reasoning runs.

### A. Agreement Matrix (Pairwise Jaccard)
For each pair of responses $(i, j)$, WBFT tokenizes the text contents and calculates their similarity using the Jaccard index:
\[J(i, j) = \frac{|T_i \cap T_j|}{|T_i \cup T_j|}\]
Where $T_i$ represents the tokenized output set of response $i$.

### B. Weighted Agreement Calculation
Using the pairwise Jaccard scores and historical agent reputations ($R$), the weighted agreement $A_i$ for a response $i$ is calculated as:
\[A_i = \sum_{j \neq i} J(i, j) \cdot R_j \cdot M_j\]
Where:
- $R_j$ is the historical reputation of agent $j$.
- $M_j$ is the domain-specific vote multiplier (e.g., higher weight for code models in programming domains).

### C. Centroid and Outlier Detection
- **Consensus Centroid:** The response with the highest weighted agreement is chosen as the centroid.
- **Byzantine Threshold:** Standard threshold defaults to $1 - f$, where $f = 1/3$ (Byzantine fraction). The minimum accepted agreement is $(1 - f) \times \max(A_i)$.
- **Outlier Flag:** Any response whose Jaccard similarity to the consensus centroid drops below the outlier threshold ($\text{Jaccard} < 0.15$) is flagged as an outlier and rejected.

---

## 3. RWA-BFT: Reputation-Weighted Asynchronous BFT

Implemented in [`cortex/consensus/rwa_bft.py`](file://~/30_CORTEX/cortex/consensus/rwa_bft.py), RWA-BFT validates fact state changes and proposed rule modifications submitted by evolutionary agents.

### A. Supermajority Condition
For a fact or state modification to be accepted, the sum of reputations of the approving validators must constitute a supermajority of the total active reputation:
\[\sum_{i \in Validators_{\text{FOR}}} R_i > \frac{2}{3} \sum_{k=1}^N R_k\]

### B. Markov Reputation Update Protocol
After each consensus round, agent reputations are updated recursively to reward consensus alignment and penalize malicious/faulty behaviors:
\[R_i^{(t+1)} = \lambda \cdot R_i^{(t)} + (1-\lambda) \cdot \Phi(v_i, V_{\text{final}})\]
Where:
- $\lambda \in [0, 1]$ is the historical memory factor (default: $0.85$).
- $v_i$ is the vote cast by agent $i$, and $V_{\text{final}}$ is the final consensus verdict.
- $\Phi$ is the payoff function:
  - **$+1.0$** if the agent voted with consensus (correct).
  - **$-3.0$** if the agent submitted a Byzantine fault (e.g., tampering attempt, payload manipulation).
  - **$0.0$** if the agent abstained.

---

## 4. GEACL: Gossip-Enabled Async Consensus Ledger

Implemented in [`cortex/consensus/geacl.py`](file://~/30_CORTEX/cortex/consensus/geacl.py), GEACL serves as the orchestration layer mapping local consensus decisions to distributed P2P topologies.

```text
[Node Local Proposal] 
       ↓
[WBFT Consensus Evaluation] (Centroid / Outlier check)
       ↓
[GEACL Coordinator] ─── (Generates SHA-256 Semantic Digest)
       ↓
[Gossip P2P Propagation] (GossipProtocol state sync to network peers)
```

When a peer node proposes a commit (e.g. tool execution, codebase modification):
1. **Local Resolution:** The local `GEACLCoordinator` runs `WBFT.evaluate()` to identify the winning consensus response.
2. **Digest Generation:** A semantic digest (SHA-256 hash) of the agreed action intent is generated.
3. **P2P Gossip Broadcast:** The digest is broadcasted asynchronously to peer nodes via `GossipProtocol` ([gossip.py](file://~/30_CORTEX/cortex/extensions/ha/gossip.py)) to maintain a synchronized replicated state ledger across the Swarm.
