# ADR-0004: Computational Jurisdiction Protocol (CJP)

## Status
**Proposed**

## Purpose
Establecer Fronteras Jurisdiccionales (Jurisdiction Boundaries) estrictas dentro del motor cognitivo (MOSKV-1). El objetivo es impedir que dominios asimétricos (ej. `Research Domain`) emitan eventos críticos pertenecientes a otros dominios (ej. `Financial Settlement Event`), previniendo la escalada de privilegios a nivel ontológico.

## Core Axioms

### A1: Jurisdiction Boundary
El Ledger es particionado lógicamente. Ningún nodo puede cristalizar un evento fuera de la jurisdicción para la que fue autorizado, independientemente de su nivel de autonomía.

### A2: Signature over Trust
Cada evento escrito en el Ledger debe ir acompañado de una `jurisdiction_signature` verificable que valide la autorización del emisor para ese `EventEnvelope` y `fact_type`.

---

## Architectural Definitions

### 1. Jurisdiction Ontology

```python
class Jurisdiction:
    namespace: str
    allowed_nodes: set
    allowed_models: set
    allowed_tools: set
```

**Dominios Canónicos:**
* `Research`
* `Code`
* `Audit`
* `Finance`
* `Governance`
* `Memory`

### 2. The Execution Chain

La cadena de reconstrucción y ejecución integra la jurisdicción como etapa de validación obligatoria:

```text
Event Ledger
      ↓
Replay Engine
      ↓
Projection Engine
      ↓
Jurisdiction Validator
      ↓
Execution Kernel
      ↓
Audit Shadow Layer
```

### 3. Cross-Jurisdiction Subpoenas (Bridges)
Cuando la Jurisdicción A (ej. `Research`) necesita influir en la Jurisdicción B (ej. `Code`), no puede cristalizar directamente en B. Debe emitir un fact de tipo `BRIDGE` en su propio namespace solicitando la acción. La Jurisdicción B deberá leer la solicitud (mediante su Replay) y decidir autónomamente si produce la mutación bajo su propia firma.

---

## Failure Modes

### F1: Jurisdiction Override (Escalada Ontológica)
* **Amenaza**: Un nodo de exploración web (`Research`) descubre credenciales y muta directamente un vector de persistencia productivo (`Code`).
* **Mitigación**: `Jurisdiction Validator` intercepta el `EventEnvelope`. Al detectar firma inválida para el namespace destino, el evento se marca como `INVALID` (o se aísla en la `Audit Shadow Layer`) y el `Execution Kernel` aborta.

### F2: Cross-contamination
* **Amenaza**: Snapshots semánticos fusionan memoria de `Governance` con memoria de `Research`, envenenando las inferencias de gobernanza.
* **Mitigación**: Segregación criptográfica de grafos proyectados. `ProjectionEngine` materializa sub-grafos por jurisdicción con reglas de visibilidad unidireccional.

---

## Result
El sistema abandona el modelo de permisos estáticos y adopta un **Modelo Jurisdiccional**. Los agentes operan dentro de su estado legal computable. La soberanía se mantiene distribuida, auditable y topológicamente aislada.
