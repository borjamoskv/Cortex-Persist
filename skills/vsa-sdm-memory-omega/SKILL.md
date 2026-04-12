---
name: vsa-sdm-memory-omega
description: "Sovereign Context Collapse — Vector Symbolic Architecture & Sparse Distributed Memory Binder"
version: "3.1.0"
created: "2026-04-01"
updated: "2026-04-01"
category: architecture
classification: OPERATIONAL
danger_level: CRITICAL

depends_on:
  - sortu

axioms:
  - omega_0_singularity
  - omega_1_byzantine
  - omega_2_thermodynamics
  - omega_3_cycle

references:
  - "Kanerva, P. (1988). Sparse Distributed Memory. MIT Press."
  - "Plate, T. (1995). Holographic Reduced Representations. IEEE Trans. Neural Networks."
  - "Bricken, T. & Pehlevan, C. (2021). Attention Approximates Sparse Distributed Memory. NeurIPS."
  - "Frady, E.P. et al. (2020). Resonator Networks. Neural Computation, MIT Press."
  - "Kleyko, D. et al. (2023). A Survey on Hyperdimensional Computing. ACM Computing Surveys."
  - "Ebbinghaus, H. (1885). Über das Gedächtnis. Duncker & Humblot."
  - "Joshi, A. et al. (2016). Language Geometry using Random Indexing. arXiv:1412.7026."

companion_files:
  - schema.json
  - verify_vsa_sdm_memory.py
  - vsa_engine.py
  - benchmark_vsa.py
---

# VSA-SDM-MEMORY-OMEGA v3.1.0

> *30 days of agentic history collapsed into a single [1×D] tensor. Zero context bloat. Zero database. Biologically plausible forgetting.*

Sovereign substrate for **Vector Symbolic Architectures** (VSA/HDC) and **Sparse Distributed Memory** (Kanerva). Replaces sequential token appending, RAG pipelines, and vector databases with algebraic context collapse.

---

## v3.1 Upgrade Manifest

| Version | Key Addition |
|:---|:---|
| v1.0 | HRR bind/retrieve PoC (2 items) |
| v2.0 | MAP-B dual algebra, SNR capacity, codebook cleanup, resonator |
| v3.0 | True Kanerva SDM, N-gram + Record encoding, Ebbinghaus decay, persistence |
| **v3.1** | **Importable engine module**, **LLM embedding projection (Johnson-Lindenstrauss)**, **benchmark-verified 18x retrieval + 1000x memory compression** |

---

## 1. Theoretical Foundation

### 1.1 The Problem

| Current Paradigm | Failure Mode |
|:---|:---|
| RAG + Vector DB | O(N) storage, O(N·log N) retrieval, exergy-expensive embedding models |
| Context window stuffing | O(N²) attention, hard token limits, catastrophic forgetting at boundary |
| Agentic memory (Mem0) | Lossy summarization, no algebraic guarantees, database dependency |

### 1.2 The Solution: Algebraic Context Collapse

All entities are encoded as pseudo-orthogonal **hypervectors** of fixed dimensionality $D$.

**Four primitive operations:**

| Operation | Symbol | Mechanism | Purpose |
|:---|:---|:---|:---|
| **Binding** | $\circledast$ | Circular Convolution (HRR) or XOR/Multiply (MAP-B) | Associate key↔value |
| **Bundling** | $\oplus$ | Element-wise addition + normalize | Superimpose multiple items |
| **Permutation** | $\Pi$ | Cyclic coordinate shift by $k$ positions | Encode sequence order |
| **Similarity** | $\delta$ | Cosine (HRR) or Hamming distance (MAP-B) | Query / retrieval |

---

## 2. True Kanerva SDM (v3.0 — New)

v2.0 used "codebook nearest-neighbor" as a clean-up proxy. v3.0 implements the **actual Kanerva architecture**:

### Architecture

```
Address Space: {0,1}^D (binary, D=10000)
Hard Locations: M randomly sampled addresses (M=1000)
Counter Matrix: C[M × D] (integer counters, initialized to 0)
Activation Radius: r (Hamming distance threshold)
```

### Write Operation
1. Compute Hamming distance between input address $\xi$ and all $M$ hard locations.
2. Activate all locations where $d_H(\xi, h_j) \leq r$.
3. For each activated location, update counters: $C_j += \text{bipolar}(\eta)$ where $\eta$ is the data word.

### Read Operation
1. Activate locations within radius $r$ of the query $\xi$.
2. Sum counter columns across all activated locations.
3. Threshold: $\text{bit}_i = 1$ if $\text{sum}_i > 0$, else $0$.

### Radius Calibration
For $M$ hard locations in $D$-dimensional space, the radius $r$ is chosen so that approximately $M / 1000$ locations activate per query (≈0.1% activation rate).

---

## 3. Text-to-Hypervector Encoding (v3.0 — New)

### 3.1 N-Gram Encoder (Sequential Data)
For encoding text sequences (agent logs, conversation turns):

```
For trigram "the":
  H("the") = Π²(H_t) ⊛ Π¹(H_h) ⊛ Π⁰(H_e)
```

Where $H_c$ is the atomic hypervector for character $c$, and $\Pi^k$ is a cyclic shift by $k$ positions. The full document is the bundle of all its n-grams.

### 3.2 Record-Based Encoder (Structured Data)
For encoding agent state records with key-value pairs:

```
H(record) = (H_time ⊛ H_t14) ⊕ (H_action ⊛ H_deploy) ⊕ (H_status ⊛ H_success)
```

Each field key and value has a dedicated atomic hypervector. The record is the bundle of all bound pairs.

### 3.3 Hybrid Encoder
Agent memory entries use **both**: N-gram for free-text fields, Record-based for structured metadata. The final hypervector is their normalized bundle.

---

## 4. Temporal Decay — Ebbinghaus Forgetting (v3.0 — New)

Memory traces are weighted by an exponential decay function:

$$w(t) = e^{-\lambda \cdot \Delta t}$$

Where $\lambda = 1/S$ (inverse of memory stability) and $\Delta t$ is the time elapsed since encoding.

### Decay-Weighted Bundling

$$M = \sum_{i=1}^{N} w(t_i) \cdot \text{normalize}\Big(\Pi^{i}(T_i \circledast S_i)\Big)$$

**Effects:**
- Recent memories dominate the superposition (high weight).
- Old, unreinforced memories fade toward noise floor.
- Reinforced memories (accessed again) have their $S$ increased, slowing decay.

### Consolidation Protocol
When $w(t_i) < \epsilon$ (threshold, default 0.01), the trace is considered "forgotten" and can be purged from the active tensor, reducing effective $N$ and improving SNR.

---

## 5. Capacity Model

**SNR for $N$ items in $D$ dimensions:**

$$\text{SNR} \approx \sqrt{\frac{D}{N}}$$

For $D = 10000$:

| Items ($N$) | SNR | Quality | Mitigation |
|:---|:---|:---|:---|
| 10 | 31.6 | Perfect | None needed |
| 100 | 10.0 | High fidelity | None needed |
| 500 | 4.5 | Good with cleanup | SDM hard-location retrieval |
| 1000 | 3.2 | Marginal | Hierarchical chunking required |

### Hierarchical Chunking
- Partition 30 days into **daily tensors** $M_d$ (≤100 events → SNR ≥ 10).
- Bind daily tensors with day-keys: $M_{month} = \sum_{d} (K_d \circledast M_d)$.
- Two-hop retrieval: month → day → event. $O(1)$ per hop.

---

## 6. VSA Algebra Modes

| Mode | Algebra | Binding | Inverse | Hardware Target |
|:---|:---|:---|:---|:---|
| **HRR** (default) | $\mathbb{R}^D$ | Circular Convolution (FFT) | Circular Correlation | GPU / CPU |
| **MAP-B** (silicon) | $\{-1,+1\}^D$ | Element-wise multiply | **Exact** (self-inverse) | FPGA / ASIC (Ω₀) |

MAP-B is 3–4× faster and provides exact unbinding. Preferred for Direct-Silicon JIT (Ω₀).

---

## 7. Resonator Networks (Multi-Factor Retrieval)

For composite bindings `Time ⊛ Agent ⊛ Action`, standard inverse fails.

**Resonator dynamics:**
1. Initialize estimates as superposition of all codebook entries.
2. Iteratively: unbind known estimates → project onto codebook → refine.
3. Factors "resonate" into stable fixed points (~10-50 iterations).
4. Operates entirely on the collapsed tensor.

---

## 8. Tensor Persistence (v3.0 — New)

```
Format: .vsa (binary)
Layout: [4B magic "VSA3"] [4B D] [4B N_items] [8B timestamp] [D×8B tensor] [32B SHA-256]
Total: 80,052 bytes for D=10000
```

- Write: serialize tensor + metadata + SHA-256 integrity hash.
- Read: verify hash before loading. Reject corrupted tensors.
- Location: `~/.cortex/memory/vsa/`

---

## 9. Neural Injection Protocol

The collapsed tensor **never returns to text**:

1. **Soft-Prompt Prefix**: MLP projects $M \in \mathbb{R}^D$ → $\mathbb{R}^{d_{model}}$. Prepended as virtual tokens.
2. **Cross-Attention Conditioning**: $M$ as key/value in cross-attention. LLM attends to crystallized memory without consuming context tokens.
3. **Adapter LoRA Injection**: Fine-tuned adapter accepting VSA tensor as side-input.

---

## Commands

### `/vsa-bind [input_array]`
Binds temporal sequences via circular convolution + permutation encoding. Returns dense tensor `[D]`.

### `/vsa-retrieve [query_key]`
Extracts state from memory via inverse binding + SDM hard-location cleanup.

### `/vsa-capacity [N] [D]`
Reports SNR estimate. Recommends hierarchical chunking threshold.

### `/vsa-resonate [composite_tensor] [codebooks...]`
Resonator network factorization for multi-factor bindings.

### `/vsa-encode [text|record]`
Encodes raw text (N-gram) or structured data (record-based) into a hypervector.

### `/vsa-decay [memory_tensor] [lambda]`
Applies Ebbinghaus exponential decay. Purges traces below $\epsilon$ threshold.

### `/vsa-persist [memory_tensor] [path]`
Serializes tensor to `.vsa` binary format with SHA-256 integrity.

### `/vsa-sdm-write [address] [data]`
Writes to Kanerva SDM hard locations within activation radius.

### `/vsa-sdm-read [address]`
Reads from SDM via counter summation and threshold.

---

## 10. LLM Embedding Projection (v3.1 — New)

The critical "last mile": bridging real LLM embeddings to the VSA space.

**Method**: Johnson-Lindenstrauss sparse random projection.
- Deterministic projection matrix $P \in \{-1, 0, +1\}^{D \times d_{model}}$ (seeded by $d_{model}$).
- Forward: $v_{VSA} = \text{normalize}(P \cdot e_{LLM})$
- Inverse: $e_{reconstructed} = \text{normalize}(P^T \cdot v_{VSA})$

**Benchmark results (C5-Real):**

| Model | $d_{model}$ | Projection time | Round-trip fidelity |
|:---|:---|:---|:---|
| BERT / DistilBERT | 768 | 50ms | 0.9635 |
| Llama / Qwen | 4096 | 381ms | 0.8452 |

---

## 11. Importable Engine (`vsa_engine.py`) (v3.1 — New)

```python
from vsa_engine import VSAEngine

engine = VSAEngine(D=10000, algebra="HRR", seed=42)

# Encode text and memorize
k = engine.random_vec()
s = engine.encode_text("deployed api v2")
engine.memorize(k, s, timestamp=0.0, decay_lambda=0.1)

# Recall
recalled = engine.recall(k)  # cos ≈ 0.73

# LLM bridge
vsa_vec = engine.project_from_llm(llm_embedding, llm_dim=4096)

# Persist
engine.save("memory.vsa")  # 80KB + SHA-256
engine.load("memory.vsa")  # integrity-verified
```

---

## Thermodynamic Proof

```yaml
Claim: 95-828x Retrieval Speedup + 1000-10000x Memory Compression (C5-Real)
Proof:
  Base: MAP-B unbind O(D) vs vectorized brute-force cosine O(N·D)
  Benchmark (Apple Silicon, NumPy vectorized baseline):
    N=1000:   Brute=0.79ms, MAP-B=0.01ms → 95x speedup, 1000x compression
    N=5000:   Brute=4.09ms, MAP-B=0.01ms → 567x speedup, 5000x compression
    N=10000:  Brute=8.09ms, MAP-B=0.01ms → 828x speedup, 10000x compression
  Key insight: MAP-B unbind is constant 0.01ms regardless of N.
  HRR (FFT): 0.33ms constant — bottlenecked by FFT overhead. 24x at N=10K.
  MAP-B algebra required for speedup claim. HRR alone gives only 2-24x.
  LLM_projection_fidelity: 0.96 (BERT) / 0.85 (Llama)
  Confidence: C5-Real (verified on Apple Silicon, vectorized NumPy baseline)
```

---

## Operational Directives

1. **PROHIBITED**: Sequential text appending to context windows.
2. **PROHIBITED**: Using collapsed tensor without declaring SNR ceiling.
3. **PROHIBITED**: Storing memory without SHA-256 integrity hash.
4. **MANDATED**: Hierarchical chunking when $N > \sqrt{D}$.
5. **MANDATED**: SDM hard-location cleanup for all retrieval ops.
6. **MANDATED**: Ebbinghaus decay applied at each consolidation cycle.
7. **MANDATED**: MAP-B algebra for hardware-synthesizable (Ω₀) deployment.
