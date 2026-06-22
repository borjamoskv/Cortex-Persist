pub mod ast;
pub mod merkle;
pub mod logger;
pub mod mtk;
pub mod fixed60;
pub mod causal;
pub mod topology;

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
    
    Ok(())
}
