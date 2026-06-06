# CORTEX-Persist MCP Server Registry Submission

> **C5-REAL Execution**  
> This document contains the exact metadata and README contents required to list `cortex-persist` in the official [MCP Servers Registry](https://github.com/modelcontextprotocol/servers).

---

## 1. Registry JSON Entry (`servers.json`)

To be appended to the official `servers.json` registry file:

```json
{
  "cortex-persist": {
    "name": "cortex-persist",
    "description": "Cryptographic memory integrity, audit trails, and verifiable lineage for AI agents.",
    "runtime": "python",
    "commands": [
      "cortex-mcp"
    ],
    "repo": "https://github.com/borjamoskv/Cortex-Persist",
    "tags": [
      "memory",
      "storage",
      "audit",
      "compliance",
      "vector-search"
    ],
    "author": "borjamoskv.com",
    "version": "1.0.0"
  }
}
```

---

## 2. README Snippet

To be added to the registry's main or category READMEs (e.g., under "Memory and Storage"):

```markdown
### 🧠 CORTEX-Persist

A Local-First Sovereign Trust layer that provides tamper-evident memory infrastructure for AI agents.

- **Hash-Chained Ledger**: SHA-256 blocks for facts and decisions, ensuring full EU AI Act Art. 12 traceability.
- **Tripartite Memory**: L1 Working, L2 Vector (sqlite-vec + ONNX), L3 Episodic ledger.
- **Multi-Tenant**: Cryptographic data isolation (`tenant_id`) enforced at all memory layers.
- **High Performance**: Zero-GIL Rust dispatch for O(1) throughput bypassing Python limitations.

**Usage:**
```json
{
  "mcpServers": {
    "cortex-persist": {
      "command": "uvx",
      "args": ["cortex-persist[mcp]", "cortex-mcp"]
    }
  }
}
```

*For advanced capabilities (compliance auditing, genesis creation, mega-tools), set `CORTEX_MCP_FULL=1` in the `env` configuration.*
```

---

## 3. Supported MCP Tools Summary

By default, the server exposes safe, core memory primitives. To enable the full suite of 35+ tools (compliance, Genesis Engine, Megatools), configure `CORTEX_MCP_FULL=1`.

### Default Core Tools
*   `cortex_store`: Store a fact in CORTEX memory. Immune Membrane + MCPGuard validated.
*   `cortex_search`: Semantic + text hybrid search across CORTEX memory.
*   `cortex_status`: Get CORTEX system status and metrics (fact counts, DB size, MCP metrics).
*   `cortex_embed`: Generate embedding vector for text.
*   `cortex_embed_status`: Show current embedding provider configuration.

### Gated Tools (`CORTEX_MCP_FULL=1`)
*   **Compliance & Trust**: `cortex_ledger_verify`, `cortex_audit_trail`, `cortex_verify_fact`, `cortex_compliance_report`, `cortex_decision_lineage`
*   **Pipeline & Swarm**: `cortex_run`, `cortex_run_async`, `cortex_cancel`, `cortex_pipeline_status`, `cortex_swarm_dispatch`
*   **Advanced Logic**: `cortex_reality_weaver`, `cortex_entropy_cracker`, `cortex_temporal_nexus`, `cortex_hilbert_omega`
*   **Genesis Engine**: `cortex_genesis_create`, `cortex_genesis_preview`, `cortex_genesis_templates`
*   **System Health**: `cortex_health_check`, `cortex_health_report`
