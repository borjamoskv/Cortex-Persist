use pyo3::prelude::*;
use pyo3::types::PyString;
use sha3::{Digest, Sha3_256};

#[pyfunction]
pub fn hash_ast(py: Python, source_code: &str, compiler_version: &str) -> PyResult<String> {
    // Import Python's built-in ast module
    let ast_module = py.import("ast")?;
    
    // Parse the source code into an AST node
    let ast_node = ast_module.getattr("parse")?.call1((source_code,))?;
    
    // Dump the AST node to a canonical string representation
    // ast.dump ignores comments and whitespace by design.
    let dumped_ast: &PyString = ast_module.getattr("dump")?.call1((ast_node,))?.downcast()?;
    let ast_str = dumped_ast.to_str()?;

    // Create the SHA3-256 hash
    let mut hasher = Sha3_256::new();
    hasher.update(ast_str.as_bytes());
    hasher.update(b"||"); // separator
    hasher.update(compiler_version.as_bytes());
    
    let result = hasher.finalize();
    Ok(hex::encode(result))
}

#[pyfunction]
pub fn generate_evidence_hash(commit_hash: &str, ast_fingerprint: &str) -> PyResult<String> {
    let mut hasher = Sha3_256::new();
    hasher.update(commit_hash.as_bytes());
    hasher.update(ast_fingerprint.as_bytes());
    
    let result = hasher.finalize();
    Ok(hex::encode(result))
}
