pub mod ast;
pub mod merkle;
pub mod logger;
pub mod mtk;
pub mod fixed60;
pub mod causal;
pub mod topology;
pub mod shim;

use pyo3::prelude::*;

#[pymodule]
fn cortex_core_rs(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(ast::hash_ast, m)?)?;
    m.add_function(wrap_pyfunction!(ast::generate_evidence_hash, m)?)?;
    m.add_function(wrap_pyfunction!(merkle::batch_merkle_root, m)?)?;
    m.add_function(wrap_pyfunction!(logger::log_ast_check, m)?)?;
    
    // Add MTK module classes
    m.add_class::<mtk::ast_parser::ASTProjector>()?;
    m.add_class::<mtk::authorizer::MTKAuthorizer>()?;
    
    // Add C5-REAL Cognitive Kernel classes
    m.add_class::<fixed60::Fixed60>()?;
    m.add_class::<topology::CognitiveState>()?;

    // Add Shim bindings
    m.add_function(wrap_pyfunction!(shim::verify_ephemeral_token, m)?)?;
    m.add_function(wrap_pyfunction!(shim::mint_ephemeral_token, m)?)?;
    m.add_function(wrap_pyfunction!(shim::ingest_reality_claim, m)?)?;
    m.add_function(wrap_pyfunction!(shim::validate_metric_json, m)?)?;
    m.add_function(wrap_pyfunction!(shim::validate_exergy_mutation, m)?)?;
    m.add_function(wrap_pyfunction!(shim::init_c5_gate_1_schema, m)?)?;
    m.add_function(wrap_pyfunction!(shim::verify_causal_assertion, m)?)?;
    m.add_function(wrap_pyfunction!(shim::execute_mee_transfer, m)?)?;
    m.add_function(wrap_pyfunction!(shim::calculate_entropy_b60, m)?)?;
    m.add_function(wrap_pyfunction!(shim::compute_friston_penalty, m)?)?;
    m.add_function(wrap_pyfunction!(shim::authorize_sqlite_mutation, m)?)?;
    m.add_class::<shim::ExergyRouter>()?;
    m.add_class::<shim::RetrievalNode>()?;
    m.add_class::<shim::RetrievalGraph>()?;
    
    Ok(())
}
