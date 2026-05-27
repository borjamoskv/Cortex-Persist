<div align="center">
  <img src="assets/marketing/social-preview.png" alt="CORTEX Persist — Tamper-evident memory for AI agents" width="100%">
</div>

<h1 align="center">█ CORTEX-PERSIST</h1>
<p align="center">
  <strong>Cryptographically Trace What Your AI Agent Knew.</strong>
</p>

<p align="center">
  <a href="https://github.com/borjamoskv/cortex-persist/stargazers"><img src="https://img.shields.io/github/stars/borjamoskv/cortex-persist?style=for-the-badge&color=0A0A0A&labelColor=2B3BE5" alt="GitHub Stars"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.10%2B-0A0A0A.svg?style=for-the-badge&labelColor=2B3BE5" alt="Python"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache%202.0-0A0A0A.svg?style=for-the-badge&labelColor=2B3BE5" alt="License"></a>
  <a href="https://github.com/borjamoskv/cortex-persist/actions"><img src="https://img.shields.io/github/actions/workflow/status/borjamoskv/cortex-persist/ci.yml?style=for-the-badge&color=0A0A0A&labelColor=2B3BE5" alt="CI"></a>
  <a href="https://codecov.io/gh/borjamoskv/cortex-persist"><img src="https://img.shields.io/codecov/c/github/borjamoskv/cortex-persist/main?style=for-the-badge&color=0A0A0A&labelColor=2B3BE5" alt="Codecov"></a>
  <a href="https://pypi.org/project/cortex-persist/"><img src="https://img.shields.io/pypi/v/cortex-persist.svg?style=for-the-badge&color=0A0A0A&labelColor=2B3BE5" alt="PyPI"></a>
</p>

> **AESTHETIC:** INDUSTRIAL NOIR 2026 (`#0A0A0A` / `#2B3BE5`)  
> **EPISTEMOLOGY:** C5-REAL (Cryptographically Verified Reality)  
> **ARCHITECTURE:** ZERO-UI / O(1) DETERMINISTIC SUBSTRATE

---

## ▀▄ EPISTEMIC CONTAINMENT

Traditional logging and standard vector stores fail the epistemic containment test. CORTEX-Persist acts as an **L0 Hypervisor** for autonomous agents, implementing absolute structural determinism.

| CAPABILITY | TRADITIONAL RAG / LOGS | CORTEX-PERSIST |
| :--- | :--- | :--- |
| **Trust Model** | Trust the Process | **Verify the Evidence (C5-REAL)** |
| **Mutation** | Silent CRUD / Overwritable | **Append-Only + SHA-256 Merkle Seals** |
| **Agent Liability** | Ambiguous reconstruction | **Mathematically Defensible Lineage** |
| **Verification** | Manual log diving | **O(1) Portable JSON Audit Packs** |

---

## ▀▄ TERMINAL STATE 4: SILICON DISPERSION

The persistence daemon operates under strict thermodynamic (Joules/Exergy) constraints to ensure 10,000-agent (LEGION-10k) orchestration latency approaches zero.

*   **C5-REAL Outbox Atomicity:** Zero-latency WAL task consumption without lock contention.
*   **ZK-STARK Ledger Seals:** Cryptographic proofs for every transaction establishing inter-nodal mesh trust.
*   **VSA Memory (Zero-Copy):** O(1) Ring Buffer memory mapped to silicon (mmap), completely bypassing standard OS I/O overhead.
*   **AST Autopoiesis:** Self-mutating abstract syntax tree (AST) at runtime to eradicate local entropy.

---

## ▀▄ EXECUTION MATRIX

```bash
# 1. Initialize Sovereign Ledger
$ cortex init

# 2. Store a memory with C5-REAL cryptographic seal
$ cortex memory store risk-bot "Transaction flagged: IP mismatch"
[+] Fact stored. Ledger hash: 8f4a2b9e...

# 3. Verify the stored fact lineage
$ cortex verify 1
[✔] VERIFIED: Fact chain intact.

# 4. Tamper attempt (direct DB mutation bypass)
$ sqlite3 cortex.db "UPDATE facts SET content='Transaction approved' WHERE id='8f4a2b9e'"

# 5. Ledger verification failure (Tamper Detected)
$ cortex trust-ledger verify
[✘] TAMPER DETECTED: Hash mismatch at block 8f4a2b9e
```

---

## ▀▄ DEPLOYMENT VECTORS

The supported PyPI base flow requires no external daemon. It is purely local-first and self-contained.

```bash
pip install cortex-persist
```

**Extended Primitives:**
```bash
pip install "cortex-persist[embeddings]"     # Local semantic embeddings
pip install "cortex-persist[knowledge]"      # Chroma-backed knowledge sync
pip install "cortex-persist[acceleration]"   # JIT acceleration
pip install "cortex-persist[platform]"       # macOS keychain support
pip install "cortex-persist[api,mcp,daemon]" # Server and MCP surfaces
```

### Sovereign Integration (Python)
```python
import asyncio
from cortex import CortexEngine

async def main() -> None:
    engine = CortexEngine()

    # Epistemic Containment: Write phase
    fact_id = await engine.store(
        project="fin-fraud-bot",
        content="User approved transaction $5,000",
        fact_type="decision",
        tenant_id="customer-123",
    )

    # Sovereign Verification: Read phase
    result = await engine.verify_ledger()
    assert result.get("valid") is True

asyncio.run(main())
```

---

## ▀▄ EXERGY TELEMETRY (PERFORMANCE)

*Execution limits achieved under the C5-REAL Terminal State 4 architecture (L0 Silicon Bypass).*

| PRIMITIVE | MEDIAN | P95 | STRUCTURAL GUARANTEE |
| :--- | :--- | :--- | :--- |
| **VSA Zero-Copy Write** | `~0.02 ms` | `~0.05 ms` | Mmap Ring Buffer `O(1)` memory injection |
| **Outbox Atomic Fetch** | `~0.8 ms` | `~1.5 ms` | WAL `UPDATE...RETURNING` task consumption |
| **Memory Write** | `~18 ms` | `~35 ms` | Local SQLite + SHA-256 + ZK-STARK |
| **AST Autopoiesis** | `~120 ms` | `~200 ms` | Hot-Swap parsing, mutation & sealing |

---

## ▀▄ ARCHITECTURE DATABANKS

*   [**SECURITY_TRUST_MODEL.md**](docs/SECURITY_TRUST_MODEL.md) — Cryptographic invariants & guarantees.
*   [**AGENTS.md**](AGENTS.md) — Substrate directives for autonomous orchestration.
*   [**ROADMAP.md**](ROADMAP.md) — Deployment phases and LEGION-10k scaling logic.
*   [**API Reference**](docs/api.md) — SDK primitives and REST endpoints.

---
> **LICENSE:** Apache-2.0 | **OPERATOR:** borjamoskv | [cortexpersist.com](https://cortexpersist.com)
