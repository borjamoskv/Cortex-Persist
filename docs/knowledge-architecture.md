# Knowledge Architecture: CORTEX ↔ NotebookLM

> **Doctrine v1.0** — Established 2026-03-02
> This document codifies the epistemic relationship between CORTEX (Operational Memory) and NotebookLM (Documentary Consultation).

---

## 1. The Tri-Layer Knowledge Stack

To prevent epistemic drift and identity divergence, the system operates on three distinct layers of knowledge:

| Layer | System | Intent | Nature | Permissions |
| :--- | :--- | :--- | :--- | :--- |
| **L0: Ground Truth** | **CORTEX** | Operational Reality | Atomic, Encrypted, Verifiable | Agent: **R/W** |
| **L1: Rendered Docs** | **MkDocs** | Architectural Blueprint | Narrative, Structured, Plaintext | Agent: **R** (via source) |
| **L2: Dialectic Lens** | **NotebookLM** | Natural Language Query | Conversational, Fluid, Transient | Agent: **Read-Only** |

### The Epistemic Imperative: Verifiable Correctness

> **Axiom Ω₃-V**: El fallo más peligroso de una IA no es la incorrección, sino la corrección no verificable.

Maintaining the **writing layer (CORTEX)** cryptographically isolated from the **synthesis layer (NotebookLM)** ensures that every "insight" generated at L2 has an immutable audit trail leading back to L0 Ground Truth.

- **Insight without Audit = Hallucination**.
- **Audit without Ground Truth = Calcification**.
- **Isolation = Sovereignty**.

### Rule Zero: CORTEX Writes, NotebookLM Reads

Agents must **never** attempt to persist decisions, facts, or state changes directly into NotebookLM. NotebookLM is a *temporary lens* for reasoning over documents, not a source of truth. If a contradiction arises between NotebookLM's output and a CORTEX fact, **CORTEX is always correct.**

---

## 2. Operational Protocol

### 2.1 The Export Pipeline

Data flows one-way: `CORTEX → Markdown Docs → NotebookLM`.

1. **CORTEX** stores the atomic reality (decisions, ghosts, bridges).
2. **CLI/Exporter** transforms encrypted/atomic data into human-readable Markdown snapshots.
3. **NotebookLM** ingests these snapshots as sources.

### 2.2 Staleness and Naming Convention

To prevent reasoning over outdated data, all sources in NotebookLM must follow the mandatory naming convention:

`cortex-{domain}-{YYYY-MM-DD}.md`

- **Domain**: Specific project or semantic cluster (e.g., `agentica`, `sap-audit`, `global`).
- **Date**: The exact day the snapshot was taken.
- **Protocol**: Any source older than **48 hours** is considered "High Risk" for operational decisions.

### 2.3 The Encryption Boundary

- **Encrypted facts (v6 AES-GCM)**: Must remain inside CORTEX. They are never exported to NotebookLM.
- **Architecture & Axioms**: Public/plaintext documentation is eligible for NotebookLM ingestion.
- **Sensitive Data**: Avoid uploading files containing PII, credentials, or financial data to personal NotebookLM accounts. Use Workspace Enterprise accounts for sensitive architectural reasoning.

---

## 3. Risks and Mitigations

### 3.1 Dual-Embedding Divergence

The system uses two different semantic spaces:

1. **CORTEX**: `MiniLM-L6-v2` (384-dim) with Read-as-Rewrite topology mutation.
2. **NotebookLM**: Proprietary Google Gemini embeddings.

**Risk**: The same query might yield different relevant context in each system.
**Mitigation**: Use NotebookLM for *synthesis* and *discovery*, but use CORTEX `recall` for *execution* and *validation*.

### 3.2 Confused Agency

**Risk**: An agent believes NotebookLM is its primary memory and stops checking CORTEX.
**Mitigation**: **Axiom Ω₃ (Byzantine Default)** applied to NotebookLM. The agent must verify any insight derived from NotebookLM against CORTEX ground truth before acting.

---

## 4. Scalability Logic

When CORTEX knowledge exceeds NotebookLM source limits (50/300 sources):

- **Fragmentation**: Split by high-level domain (e.g., `Notebook: CORTEX-Legal`, `Notebook: CORTEX-Frontend`).
- **Master Digest**: Use the `cortex_notebooklm.ipynb` logic to collapse multiple projects into a single "Master Digest" source to maximize word-count efficiency (500k words/source).

---

> *"Defining the architecture is the first act of sovereignty."* — [AGENTICA.md](file://./docs/AGENTICA.md)
