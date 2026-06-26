# Data Flow Diagrams

This document contains the structural data flow diagrams (DFDs) for CORTEX Persist core operations.

## 1. The Write-Path (Saga Pattern)
This diagram illustrates the mandatory unidirectional flow for state mutations.

```mermaid
sequenceDiagram
    participant Agent as Autonomous Agent
    participant Firewall as Memory Firewall
    participant Guardian as Persist-Guardian
    participant Ledger as Master Ledger
    participant SQLite as Persistence Layer

    Agent->>Firewall: Propose State Mutation
    Firewall->>Firewall: Secret/PII Scan & Risk Eval
    alt Risk CRITICAL
        Firewall-->>Agent: SAGA-1: Reject (P0)
    else Risk Acceptable
        Firewall->>Guardian: Forward Proposal
        Guardian->>Guardian: Verify Schema & Taint
        Guardian->>Guardian: Generate Ed25519 Signature
        Guardian->>Ledger: Append to Hash Chain
        Ledger-->>SQLite: Commit Transaction
        SQLite-->>Guardian: ACK
        Guardian-->>Agent: SAGA COMMITTED
    end
```

## 2. Audit Verification Flow
```mermaid
graph TD
    A[Audit Bundle .zip] --> B[cortex verify CLI]
    B --> C{Check Hash Chain}
    C -->|Valid| D{Check Signatures}
    C -->|Invalid| Z[TAMPER DETECTED]
    D -->|Valid| E{Check RFC3161 Timestamp}
    D -->|Invalid| Z
    E -->|Valid| F[EVIDENCE VERIFIED]
    E -->|Invalid| Z
```
