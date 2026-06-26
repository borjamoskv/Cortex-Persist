# Trust Boundaries

This document defines the strict trust boundaries within the CORTEX Persist ecosystem. Any crossing of these boundaries requires cryptographic validation and adherence to the system axioms.

## Boundary 1: The Epistemic Boundary (Generative vs. Deterministic)
- **Untrusted (C4-SIM)**: LLM outputs, agent reasoning, generative text, external API responses.
- **Boundary Control**: `Persist-Validator` and the `Memory Firewall`.
- **Trusted (C5-REAL)**: Validated schemas, ASTs, deterministic structures, signed payloads.
- **Rule**: Generative output is pure conjecture. It must be transformed into a deterministic, validatable structure before crossing into the trusted zone.

## Boundary 2: The Tenant Boundary
- **Untrusted**: Any read/write request lacking a verified `tenant_id`.
- **Boundary Control**: `Persist-Guardian` isolation controls.
- **Trusted**: Tenant-scoped SQLite contexts and vector indices.
- **Rule**: Cross-tenant data access is a P0 abort condition. Every operation must inject its context.

## Boundary 3: The Persistence Boundary
- **Untrusted**: Ephemeral RAM, temporary Python objects, unsigned state proposals.
- **Boundary Control**: The Write-Path Contract (Saga Steps 1-7).
- **Trusted**: Master Ledger, SQLite WAL, ONNX vector embeddings.
- **Rule**: No mutation occurs without an emitted `CORTEX-TAINT` signature and successful hash chain update.

## Boundary 4: The Execution Boundary
- **Untrusted**: Shell commands, filesystem reads from agents.
- **Boundary Control**: OS sandboxes, MAC isolation, Workspace paths (`~/10_PROJECTS`, `~/20_VAULT`).
- **Trusted**: The CORTEX Execution Kernel.
- **Rule**: Absolute restriction against modifying system paths (`/private/var/db`, `/System`).
