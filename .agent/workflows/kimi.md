---
description: Invoke SovereignLLM (Kimi K2.5 or other massive-context providers) for strategic planning
---

# 🧠 SovereignLLM — The Strategic Core (formerly Kimi CLI)

> [!IMPORTANT]
> **SovereignLLM** is the sovereign strategic layer of the MOSKV Swarm. The old `kimi` CLI is deprecated as doctrine. Kimi K2.5 is now simply one provider (the preferred one for massive context 1M+ tokens) within the unified SovereignLLM architecture.

## Architecture

Instead of calling a vendor-specific CLI, we now use the `SovereignLLM` interface which routes massive-context workloads to the best provider (Kimi K2.5, Gemini Pro, etc) transparently.

## Quick Start (Legacy Interface)

*Note: Scripts are being migrated to `SovereignLLM` API.*

```bash
# Verify connectivity (Legacy)
kimi mcp list

# Strategic analysis with reasoning trace
kimi --thinking "Analyze CORTEX v4.1 federation architecture for single points of failure"

# Targeted analysis on specific files
kimi --context cortex/federation.py --thinking "Review tenant isolation for data leaks"
```

## Mission Templates (Via SovereignLLM)

### 🔍 Architectural Audit

```bash
kimi --thinking "
Audit the following codebase for:
1. Single points of failure
2. Missing error boundaries
3. Circular dependencies
4. Scalability bottlenecks
Provide severity ratings (P0-P3) and concrete fixes.
" --context ~/cortex/cortex/
```

### 🛡️ Security Review

```bash
kimi --thinking "
Security review focusing on:
1. Input validation gaps
2. SQL injection vectors
3. Authentication bypass risks
4. Data poisoning surfaces
Rate each finding: CRITICAL / HIGH / MEDIUM / LOW
" --context ~/cortex/cortex/mcp/
```

### 🗺️ Strategic Roadmap

```bash
kimi --thinking "
Given the current architecture, design the next 3 waves of improvements.
For each wave: goal, files to modify, estimated complexity (S/M/L), dependencies.
Prioritize by impact/effort ratio.
" --context ~/cortex/
```

### 🔬 Code Review (Specific PR/Diff)

```bash
# Review recent changes
cd ~/cortex && git diff HEAD~5..HEAD | kimi --thinking "Review this diff for bugs, performance issues, and style violations"
```

## Swarm Integration (SovereignLLM)

The analyst specialty can be invoked from the Fractal Swarm via SovereignLLM:

```python
# In swarm mission config
{
    "agent": "sovereign-analyst",
    "provider": "kimi-k2.5",  # Or 'gemini-1.5-pro'
    "capability": "massive_context",
    "task": "Cross-project dependency analysis between CORTEX and LiveNotch"
}
```

## Auth (Kimi Provider)

When Kimi is selected as provider by SovereignLLM, OAuth via macOS Keyring is used. No API keys needed manually.

```bash
# Session check for Kimi provider
kimi mcp list  # If it responds → authenticated
```
