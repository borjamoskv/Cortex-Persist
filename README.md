# CORTEX Persist

**Tamper-evident memory and decision lineage for AI agents.**

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![CI](https://github.com/borjamoskv/Cortex-Persist/actions/workflows/ci.yml/badge.svg)](https://github.com/borjamoskv/Cortex-Persist/actions)

CORTEX is trust infrastructure for AI agents.

It sits between your runtime and your memory layer, making facts, decisions, and derived state tamper-evident. If stored context changes after the fact, verification fails. If you need to explain what an agent knew, when it knew it, and what it did next, CORTEX gives you a cryptographic trail instead of an anecdote.

Built for autonomous systems that need more than "the model said so."

## Why CORTEX

LLMs do not produce trustworthy state by default.

Once an agent reads context, stores memory, calls tools, or makes a decision, that state can drift, be overwritten, or be silently mutated by downstream systems. CORTEX adds a cryptographic evidence layer on top of your existing memory stack so that important state becomes verifiable instead of anecdotal.

## What it does

- Tamper-evident memory (append-only ledger)
- Hash-linked records (SHA-256)
- Merkle checkpoints for batch proofs
- Deterministic audit exports
- Drop-in on existing memory systems

## Use cases

- Autonomous agents → prueba de decisiones
- Multi-agent systems → trazabilidad causal
- Compliance → auditoría reproducible
- Forensics → detección de manipulación
- Trust-critical products → evidencia, no narrativa

## Architecture

```
[ Agent Runtime ]
        ↓
[ CORTEX Persist ]
        ↓
[ Memory Store ]
```

## Integration

```python
from cortex import CortexEngine
```

Done.
