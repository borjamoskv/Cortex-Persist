# ADR-0001: CORTEX vs MOSKV-1 Arquitectura Soberana

**Sustrato de persistencia y entidad cognitiva**

## Status
**Accepted**

## Decision
Separar estrictamente el sustrato de confianza persistente (CORTEX) de la entidad cognitiva operativa (MOSKV-1) mediante contratos explícitos, validación de esquema, trazabilidad criptográfica y pruebas de reemplazabilidad.

La separación es conceptual y técnica. La integración operativa existe, pero queda limitada por invariantes verificables.

## Context
El sistema requiere dos capas:
* **CORTEX**: persistencia, integridad, búsqueda, consenso y auditoría.
* **MOSKV-1**: percepción, razonamiento, decisión, ejecución y mutación controlada.

El objetivo no es fusionar memoria y agencia sin límites, sino permitir un bucle autoreferencial auditable sin corrupción del sustrato.

## Scope
**Aplica a:**
* almacenamiento de facts
* lectura semántica y estructurada
* escritura de facts y decisions
* invalidación de caché
* resolución de conflictos
* replay y auditoría
* multi-agente concurrente

**Non-goals (Fuera de alcance):**
* optimización de prompts
* mejoras estéticas del output
* memoria implícita no auditable
* escritura sin contrato
* auto-modificación del sustrato fuera de pipeline validado

---

## System Model

### CORTEX
Sistema de persistencia soberana.

**Responsibilities:**
* almacenar facts con integridad verificable
* emitir tombstones para borrado lógico
* preservar historial y linaje
* servir lectura consistente y trazable
* aplicar consenso cuando exista escritura concurrente
* rechazar entradas inválidas

**Non-responsibilities:**
* decidir acciones
* inferir intención
* compensar esquemas ambiguos
* adivinar datos faltantes

### MOSKV-1
Entidad cognitiva operativa.

**Responsibilities:**
* percibir estado actual de CORTEX
* razonar sobre facts válidos
* producir decisiones y acciones
* escribir solo mediante contratos
* mantener coherencia con versión de esquema
* no tratar caché como verdad si hay frescura dudosa

**Non-responsibilities:**
* alterar persistencia sin validación
* asumir que un fact viejo sigue siendo válido
* escribir tipos arbitrarios
* ignorar consenso

---

## Invariants

* **I1. Integrity**: Todo fact persistido debe tener hash verificable, esquema conocido y origen auditable.
* **I2. Tombstone over delete**: Nada se borra físicamente sin rastro. El borrado lógico se representa con tombstone.
* **I3. Schema closure**: `fact_type` es un enum cerrado. Valores libres están prohibidos.
* **I4. Versioned contracts**: Todo payload persistido debe declarar `schema_version`.
* **I5. Write validation**: Ninguna escritura entra sin validación de estructura, tipo, tamaño y campos obligatorios.
* **I6. Read freshness**: MOSKV-1 no puede usar una lectura si la frescura de caché excede el TTL permitido para ese dominio.
* **I7. Quorum on conflict**: Si existen múltiples escritores o estados divergentes, la cristalización requiere regla de consenso explícita.
* **I8. Deterministic replay**: Un evento persistido debe poder reproducirse determinísticamente contra el mismo esquema y producir el mismo resultado lógico.
* **I9. Separation of concern**: MOSKV-1 no conoce el backend físico de CORTEX. CORTEX no conoce el modelo cognitivo concreto de MOSKV-1.
* **I10. Auditability**: Toda mutación debe dejar rastro suficiente para reconstrucción forense.

---

## Contracts

### CORTEX read contract
**Input:** query, namespace, filters, freshness policy, schema version target
**Output:** matching facts, metadata, lineage, confidence / consensus data, tombstone state
**Rules:**
* never return untyped data without wrapper metadata
* never silently downgrade schema
* never merge incompatible records without explicit conflict marker

### CORTEX write contract
**Input:** fact payload, fact_type, schema_version, source agent id, timestamp, checksum / hash, optional consensus evidence
**Rules:**
* reject unknown fact_type
* reject payloads missing required fields
* reject malformed JSON / schema drift
* reject writes that violate policy or exceed size limits
* require tombstone for logical invalidation

### MOSKV-1 decision contract
MOSKV-1 may transform reads into decisions only when:
* source facts are valid under current schema
* freshness is within policy
* conflicts are resolved or explicitly acknowledged
* confidence thresholds are met

MOSKV-1 must emit:
* decision type
* rationale pointer to facts used
* action target
* expected side effects
* rollback / tombstone strategy when relevant

### Multi-agent contract
When more than one agent writes:
* writer identity is mandatory
* versioning is mandatory
* conflict policy is mandatory
* lock or quorum mechanism is mandatory
* last-write-wins is forbidden unless explicitly scoped and documented

---

## Data Model Minimum

**Fact:**
* `id`
* `fact_type`
* `content`
* `schema_version`
* `source_agent`
* `created_at`
* `updated_at`
* `hash`
* `parent_hash` or lineage
* `consensus_score`
* `tombstoned_at` (optional)
* `meta` (validated object)

**Decision:**
* `id`
* `decision_type`
* `inputs`
* `outputs`
* `facts_used`
* `agent_id`
* `schema_version`
* `created_at`
* `audit_hash`

---

## Failure Modes

* **F1. Stale cache**: MOSKV-1 reads outdated state and acts on obsolete facts.
  * **Effect**: divergent identity state, invalid decisions, replay mismatch
  * **Mitigation**: TTL enforcement, freshness flags, forced revalidation before write
* **F2. Invalid fact_type**: Free text or malformed enum leaks into persistence.
  * **Effect**: silent recall failure, broken filtering, corrupted downstream queries
  * **Mitigation**: hard enum validation, schema rejection at ingest
* **F3. Schema drift**: Producer and consumer disagree on payload shape.
  * **Effect**: empty query results, non-deterministic behavior, hidden failures
  * **Mitigation**: `schema_version` pinning, compatibility tests, migration gates
* **F4. False consensus**: A single agent writes with inflated confidence.
  * **Effect**: fake facts treated as verified, trust erosion
  * **Mitigation**: quorum requirements, provenance checks, confidence calibration
* **F5. Split brain**: Two agents produce contradictory writes without coordination.
  * **Effect**: conflicting truths, non-deterministic reads
  * **Mitigation**: distributed lock or compare-and-swap, conflict ledger, reconciliation workflow
* **F6. Silent tombstone failure**: A fact is considered deleted but remains reachable.
  * **Effect**: ghost facts, stale resurrection
  * **Mitigation**: tombstone index, negative assertions in read path, deletion tests
* **F7. Replay divergence**: Replaying the same event produces a different logical state.
  * **Effect**: broken auditability, unverifiable history
  * **Mitigation**: deterministic reducers, pinned schema, immutable event log
* **F8. Backend substitution leak**: MOSKV-1 depends on implementation details of CORTEX storage backend.
  * **Effect**: brittle coupling, failed migration
  * **Mitigation**: storage abstraction boundary, backend-agnostic API

---

## Test Matrix

* **T1. Backend swap test**: Replace SQLite with DuckDB.
  * *Expected*: MOSKV-1 behavior unchanged, facts preserved, reads stable
* **T2. Cognition swap test**: Replace MOSKV-1 with MOSKV-2.
  * *Expected*: CORTEX unchanged, data integrity preserved, contract compatibility maintained
* **T3. Schema rejection test**: Send invalid `fact_type`.
  * *Expected*: write rejected, no persistence side effect, audit entry created
* **T4. Stale read test**: Serve a cached fact past TTL.
  * *Expected*: cache invalidated, revalidation triggered, decision blocked or downgraded
* **T5. Tombstone test**: Mark a fact deleted logically.
  * *Expected*: fact excluded from normal reads, tombstone remains auditable, replay preserves deletion
* **T6. Conflict test**: Submit two contradictory writes from different agents.
  * *Expected*: conflict detected, no silent overwrite, quorum or reconciliation required
* **T7. Replay test**: Replay an event log from clean state.
  * *Expected*: deterministic final state, hash chain intact, no schema mismatch
* **T8. Corruption test**: Mutate stored metadata manually.
  * *Expected*: hash mismatch detected, record quarantined, audit alert emitted

---

## Acceptance Criteria

The architecture is valid only if all conditions hold:
1. data survives backend migration without semantic loss
2. agent replacement does not require storage rewrite
3. invalid writes are rejected before persistence
4. every persisted mutation is auditable
5. stale data cannot silently drive decisions
6. concurrent writers cannot overwrite each other without explicit policy
7. replay reproduces the same logical state

---

## Operational Rules
* Validate before write.
* Prefer tombstone over deletion.
* Never trust stale cache as truth.
* Never allow free-text ontology where enum is required.
* Never bypass schema versioning.
* Never collapse conflict into silence.
* Every decision must point back to facts.
* Every fact must be reconstructible.

---

## Implementation Notes
* Use explicit enums for `fact_type`.
* Add schema validation at ingestion boundary.
* Enforce TTL for semantic cache.
* Separate storage API from cognition API.
* Keep hash chains and lineage immutable.
* Require consensus metadata for writes from multiple agents.
* Treat the ledger as source of truth, not the cache.

---

## Result
CORTEX is the persistent substrate. MOSKV-1 is the active cognitive layer.
The contract between them is the sovereign boundary. If the contract is enforced, the system remains auditable, replaceable, and stable under evolution. If the contract is soft, the architecture is cosmetic.
