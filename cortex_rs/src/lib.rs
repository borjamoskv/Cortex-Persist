
pub mod edg;

use pyo3::prelude::*;
use edg::{EpistemicGraph, EpistemicNode, EpistemicStatus};

/// CORTEX-Persist Cognitive Core Rust Extension (Enterprise EDG)
#[pymodule]
fn cortex_rs(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<EpistemicStatus>()?;
    m.add_class::<EpistemicNode>()?;
    m.add_class::<EpistemicGraph>()?;
    Ok(())
}
