# RFC-004: Rust Event-Sourcing & SMT Consensus Spec

**Author:** MOSKV-1 APEX
**Date:** 2026-06-21
**Status:** DRAFT (Awaiting TLA+ Validation)
**Target:** `cortex_rs` (Event-Driven Dependency Graph)

## 1. Ontological Demotion & Conceptual Alignment
El sistema ha sido despojado de metafísica. La "epistemología" se reduce a **consistencia distribuida**.
- **EDG:** Renombrado a *Event-Driven Dependency Graph*. La estructura causal se mantiene, pero la semántica es de Event Sourcing.
- **Validation State:** `epistemic_status` ha sido renombrado a `validation_state` (`staging`, `sealed`, `rejected`).
- **Telemetry:** La `exergía` ha sido expulsada de la semántica del grafo. Pasa a ser una `cost_metric` en la capa de Observabilidad.

## 2. Rust Architecture Spec (Actix + Tokio)

### 2.1 Storage Layer: WAL & Snapshots
```rust
// cortex_rs/src/storage/wal.rs
use tokio::fs::{OpenOptions, File};
use tokio::io::AsyncWriteExt;
use serde::{Serialize, Deserialize};

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct WalEntry {
    pub tx_id: u64,
    pub timestamp: i64, // Babylon-60 integer
    pub payload: Vec<u8>,
    pub status: WalStatus,
}

#[derive(Serialize, Deserialize, Debug, Clone, PartialEq)]
pub enum WalStatus {
    Pending, // Written to WAL, waiting for Merkle root batching
    Committed, // Injected into DB, batched
}
```

### 2.2 Validation Layer: SMT Consensus
Implementación corregida del consenso de provers. Los solvers no son oráculos de verdad, son validadores de consistencia semidecidible.

```rust
// cortex_rs/src/validation/smt_consensus.rs
use std::collections::HashSet;

pub enum SmtResult {
    Sat(String),   // Proof trace
    Unsat(String), // Counterexample trace
    Unknown,
    Timeout,
}

pub struct SmtConsensus;

impl SmtConsensus {
    /// Evalúa la aserción contra Z3, CVC5 y Yices.
    /// Lógica corregida: No requiere quorum de 3/3 para "verdad".
    /// Un solo UNSAT rechaza. Un SAT tentativo aprueba.
    pub async fn evaluate(assertion: &str) -> ValidationOutcome {
        let (z3, cvc5, yices) = tokio::join!(
            invoke_z3(assertion),
            invoke_cvc5(assertion),
            invoke_yices(assertion)
        );

        let results = vec![z3, cvc5, yices];

        // Fail-fast on any UNSAT
        if results.iter().any(|r| matches!(r, SmtResult::Unsat(_))) {
            return ValidationOutcome::Rejected("UNSAT proof found".to_string());
        }

        // Accept if at least one SAT and no UNSAT
        if results.iter().any(|r| matches!(r, SmtResult::Sat(_))) {
            return ValidationOutcome::Sealed;
        }

        // Divergence or Unknown -> Escalate to manual/heavy proof trace
        ValidationOutcome::Escalate
    }
}
```

### 2.3 Graph Layer: State Isolation (Staging)
El control de acceso perfecto ("epistemic vacuum") se implementa mediante Actor-Model isolation en Actix.

```rust
// cortex_rs/src/graph/router.rs
use actix::prelude::*;

pub struct GraphActor {
    // In-memory materialized views. Staging is NEVER merged into the main read-replica.
    sealed_graph: DependencyGraph,
    staging_buffer: HashMap<u64, Node>,
}

impl Handler<QueryNode> for GraphActor {
    type Result = Option<Node>;

    fn handle(&mut self, msg: QueryNode, _: &mut Context<Self>) -> Self::Result {
        // Read queries strictly target the sealed_graph.
        // Staging buffer is entirely invisible to the global query layer.
        self.sealed_graph.get(&msg.node_id).cloned()
    }
}

impl Handler<ValidationEvent> for GraphActor {
    type Result = ();

    fn handle(&mut self, msg: ValidationEvent, _: &mut Context<Self>) {
        if msg.outcome == ValidationOutcome::Sealed {
            if let Some(node) = self.staging_buffer.remove(&msg.node_id) {
                self.sealed_graph.insert(node);
            }
        } else {
            self.staging_buffer.remove(&msg.node_id); // GC Tombstone
        }
    }
}
```

## 3. Próximo Paso
El sistema requiere modelado de corrección formal. Se solicita la instanciación de un modelo TLA+ para verificar la ausencia de *race conditions* entre el volcado del `WAL` asíncrono y el `Validation Actor`.
