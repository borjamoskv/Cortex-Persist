<!-- [C5-REAL] Exergy-Maximized -->
<div align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/marketing/social-preview.png">
    <source media="(prefers-color-scheme: light)" srcset="assets/marketing/social-preview-light.png">
    <img src="assets/marketing/social-preview.png" alt="CORTEX Persist — Tamper-evident memory for AI agents" width="100%">
  </picture>
</div>

<h1 align="center">█ CORTEX-PERSIST</h1>
<p align="center">
  <strong>Cryptographically Trace What Your AI Agent Knew.</strong><br>
  <em>Tamper-evident memory & decision lineage for AI agents. Cryptographic proof of what your agent knew.</em>
</p>

<p align="center">
  <a href="https://github.com/borjamoskv/cortex-persist/stargazers"><img src="https://img.shields.io/github/stars/borjamoskv/cortex-persist?style=for-the-badge&color=0A0A0A&labelColor=2B3BE5" alt="GitHub Stars"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.10%2B-0A0A0A.svg?style=for-the-badge&labelColor=2B3BE5" alt="Python"></a>
  <a href="https://github.com/borjamoskv/cortex-persist/actions"><img src="https://img.shields.io/github/actions/workflow/status/borjamoskv/cortex-persist/ci.yml?style=for-the-badge&color=0A0A0A&labelColor=2B3BE5" alt="CI"></a>
  <a href="https://pypi.org/project/cortex-persist/"><img src="https://img.shields.io/pypi/v/cortex-persist.svg?style=for-the-badge&color=0A0A0A&labelColor=2B3BE5" alt="PyPI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache%202.0-0A0A0A.svg?style=for-the-badge&labelColor=2B3BE5" alt="License"></a>
  <a href="https://github.com/sponsors/borjamoskv"><img src="https://img.shields.io/badge/sponsor-github-0A0A0A.svg?style=for-the-badge&labelColor=2B3BE5&logo=github" alt="Sponsor"></a>
</p>

```yaml
AESTHETIC: INDUSTRIAL NOIR 2026 (#0A0A0A / #2B3BE5)
EPISTEMOLOGY: C5-REAL (Cryptographically Verified Reality)
CORE TENET: EPISTEMIC HUMILITY (Generative output is conjecture; Evidence is absolute)
ARCHITECTURE: ZERO-UI / O(1) DETERMINISTIC SUBSTRATE
```

---

## ▀▄ QUICK DEMO (3 MINUTES)

See the C5-REAL verification loop, semantic search, and tampering detection in action instantly.

```bash
git clone https://github.com/borjamoskv/Cortex-Persist.git
cd Cortex-Persist
pip install -e ".[dev,acceleration]"

# Run the canonical tampering detection demo
python examples/demo_canonical.py
```

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/marketing/cortex_demo.gif">
  <source media="(prefers-color-scheme: light)" srcset="assets/marketing/cortex_demo_light.gif">
  <img alt="CORTEX-Persist Terminal Execution" src="assets/marketing/cortex_demo.gif" width="100%">
</picture>

---

## ▀▄ THE EPISTEMIC CONTAINMENT SHIELD

**Generative AI output is fundamentally probabilistic conjecture. Traditional logs blindly trust stochastic output.**  
CORTEX-PERSIST intercepts stochastic text, enforces a deterministic shield via Z3 SMT Guards, and commits the state to a cryptographically bound Ledger.

| CAPABILITY | TRADITIONAL RAG / LOGS | CORTEX-PERSIST |
| :--- | :--- | :--- |
| **Trust Model** | Trust the Process | **Verify the Evidence (C5-REAL)** |
| **Mutation** | Silent CRUD / Overwritable | **Append-Only + SHA-256 Merkle Seals** |
| **Agent Liability** | Ambiguous reconstruction | **Mathematically Defensible Lineage** |
| **Verification** | Manual log diving | **O(1) Portable JSON Audit Packs** |

### ZERO-FRICTION SOVEREIGN INTEGRATION
Inject the CORTEX memory substrate into any existing agent pipeline via our magic decorator.

```python
import asyncio
from cortex.magic import sovereign_persist

@sovereign_persist(memory="cortex-cloud", strict=True)
async def my_agent_chain(user_prompt: str):
    # CORTEX intercepts, verifies, and cryptographically seals memory autonomously.
    response = await llm.generate(user_prompt)
    return response
```

---

## ▀▄ ARCHITECTURE & DATA FLOW

```mermaid
graph TD
    classDef default fill:#0A0A0A,stroke:#2B3BE5,stroke-width:1px,color:#F0F0F0;
    classDef highlight fill:#2B3BE5,stroke:#CCFF00,stroke-width:1.5px,color:#FFFFFF;
    classDef guard fill:#1A1A1A,stroke:#FF0055,stroke-width:1px,color:#F0F0F0;

    subgraph Stochastic Space
        LLM[Agent Stochastic Output]:::default
    end

    subgraph Epistemic Membrane [CORTEX-Persist Containment Shield]
        direction TB
        G1[Z3 SMT Guard / Admission Gate]:::guard
        VSA[Zero-Copy VSA Ring Buffer]:::default
        mmap[( mmap Silicon Space )]:::default
        Hash[SHA-256 Block Sealing]:::default
        Merkle[Merkle Provenance Chain]:::default
    end

    subgraph Trust Substrate
        Ledger[(Append-Only AOF Ledger)]:::highlight
        Proof[Verifiable Audit Pack JSON]:::default
    end

    LLM -->|Decision / Observation| G1
    G1 -->|Passed Asserts| VSA
    VSA -->|Zero I/O Overhead| mmap
    VSA -->|Batch Commit| Hash
    Hash -->|Hash Link| Merkle
    Merkle -->|State Anchoring| Ledger
    Ledger -->|Generate| Proof
    
    style Epistemic Membrane fill:#050505,stroke:#2B3BE5,stroke-dasharray: 5 5;
    style Trust Substrate fill:#050505,stroke:#CCFF00,stroke-dasharray: 5 5;
```

---

## ▀▄ REAL-WORLD USE CASES

Check out the `examples/` directory for ready-to-run scenarios:

1. **[Automated Pricing Agent (`demo_pricing_agent.py`)](examples/demo_pricing_agent.py)**: Watch an AI modify enterprise pricing while CORTEX records a cryptographic audit trail ensuring the discount logic was sound.
2. **[Customer Support Escalation (`demo_support_approval.py`)](examples/demo_support_approval.py)**: A support bot grants a refund. CORTEX seals the decision lineage so the supervisor has mathematical proof of why the AI approved it.
3. **[Canonical Loop (`demo_canonical.py`)](examples/demo_canonical.py)**: A showcase of the full C5-REAL execution, demonstrating how the ledger reacts to malicious state tampering attempts.

---

## ▀▄ INSTALLATION & DEPLOYMENT

**Requirements:** `Python 3.10+`. Zero external daemons required.

```bash
pip install cortex-persist

# Optional Core Modules
pip install "cortex-persist[embeddings]"     # Local semantic embeddings
pip install "cortex-persist[knowledge]"      # Chroma-backed knowledge sync
pip install "cortex-persist[api,mcp,daemon]" # Web Server & MCP endpoints
pip install "cortex-persist[cloud]"          # PostgreSQL, Redis, & Qdrant scaling

```

---

## ▀▄ ARCHITECTURE DATABANKS

*   [**SECURITY_TRUST_MODEL.md**](docs/SECURITY_TRUST_MODEL.md) — Cryptographic invariants & guarantees.
*   [**AGENTS.md**](AGENTS.md) — Substrate directives for autonomous orchestration.
*   [**ROADMAP.md**](ROADMAP.md) — Deployment phases and LEGION-10k scaling logic.
*   [**API Reference**](docs/api.md) — SDK primitives and REST endpoints.

---
> **LICENSE:** Apache-2.0 | **OPERATOR:** borjamoskv | [CORTEX.ORG](https://cortexpersist.org) | [CORTEX.DEV](https://cortexpersist.dev) | [Sponsor the Engine](https://github.com/sponsors/borjamoskv)
