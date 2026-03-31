# REPO_GOVERNANCE.md — CORTEX-Persist

> "Trust is not assumed; it is computed, persisted, and verified."

## 1. Overview

CORTEX-Persist es un sustrato de memoria inmutable y auditivo para sistemas multi-agente soberanos. La gobernanza de este repositorio asegura que todas las mutaciones al estado del conocimiento sigan protocolos deterministas y resistentes a la manipulación.

## 2. The 10 Seals Protocol (AX-033)

Todo commit y toda operación de escritura en producción debe superar el pipeline de seguridad "10 Seals":

1.  **Ghost Radar**: Sin marcadores de conflicto ni código muerto.
2.  **Test Suite**: Cobertura mínima del 80% (Core).
3.  **Git State**: Alineación estricta con el DAG de la rama `main`.
4.  **Quality Gate**: Linting limpio (Ruff/E,F,W,I,UP,B,ASYNC).
5.  **Neural Connectivity**: Verificación de tokens y backends de inferencia.
6.  **Fail-Closed Guards**: Los guards de contradicción y salud bloquean el write-path ante anomalías.
7.  **Tamper Evidence**: Integridad hash-chain verificable en `entity_events`.
8.  **Tenant Isolation**: Aislamiento estricto de datos por `tenant_id`.
9.  **Exergy Verification**: Los hechos persistidos deben tener un yield score positivo.
10. **Sovereign Audit**: Seguimiento completo de la toma de decisiones vía `transactions`.

## 3. Contribution Guidelines

- **Zero-Rhetoric Mandate (Rule MOSKV)**: El código debe ser industrial, sin prosa decorativa.
- **Async-First**: Todas las operaciones IO deben ser no bloqueantes.
- **Type Safety**: Las funciones públicas deben usar type hints (`pyright` basic mode).
- **Causal Lineage**: Las mutaciones de hechos deben incluir el `signer` y el `parent_decision_id` cuando sea posible.

## 4. Maintenance & Releases

- **Versioning**: vX.Y.Zb (Beta) — Las versiones se etiquetan mediante git tags.
- **Mantenimiento**: Los dæmons de "Decalcify" y "Epistemic Breaker" se ejecutan en segundo plano para evitar el estancamiento cognitivo.

---

📝 **Governance Custodian**: borjamoskv · **Framework**: C5-Dynamic · **License**: Apache-2.0
