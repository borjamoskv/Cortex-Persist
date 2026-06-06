pub mod belief_object;
pub mod atms;
pub mod smt;

use pyo3::prelude::*;
use belief_object::{BeliefObject, BeliefState, RelationType, ProvenanceEnvelope, BeliefRelation};
use atms::AtmsGraph;
use smt::SmtLeaf;

/// CORTEX-Persist Cognitive Core Rust Extension
#[pymodule]
fn cortex_rs(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<BeliefState>()?;
    m.add_class::<RelationType>()?;
    m.add_class::<ProvenanceEnvelope>()?;
    m.add_class::<BeliefRelation>()?;
    m.add_class::<BeliefObject>()?;
    m.add_class::<AtmsGraph>()?;
    m.add_class::<SmtLeaf>()?;
    Ok(())
}

