
pub mod belief_object;
pub mod atms;
pub mod smt;
pub mod storage_guard;
pub mod ctre_guardian;
pub mod auth;
pub mod ultramap;
pub mod belief_scheduler;
pub mod se_crdt;

use pyo3::prelude::*;
use belief_object::{BeliefObject, BeliefState, RelationType, ProvenanceEnvelope, BeliefRelation};
use atms::AtmsGraph;
use smt::{SmtLeaf, SparseMerkleTree};
use ultramap::UltramapSubstrate;
use belief_scheduler::BeliefPlaneScheduler;
use se_crdt::SemanticState;

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
    m.add_class::<SparseMerkleTree>()?;
    m.add_class::<UltramapSubstrate>()?;
    m.add_class::<BeliefPlaneScheduler>()?;
    m.add_class::<SemanticState>()?;
    m.add_function(wrap_pyfunction!(storage_guard::validate_proposal, m)?)?;
    m.add_function(wrap_pyfunction!(storage_guard::detect_poisoning, m)?)?;
    m.add_function(wrap_pyfunction!(ctre_guardian::ctre_atomic_commit, m)?)?;
    m.add_function(wrap_pyfunction!(auth::hash_password, m)?)?;
    m.add_function(wrap_pyfunction!(auth::verify_password, m)?)?;
    Ok(())
}
