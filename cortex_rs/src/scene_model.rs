use pyo3::prelude::*;
use serde::{Deserialize, Serialize};

#[pyclass]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SceneState {
    #[pyo3(get, set)]
    pub id: String,
    #[pyo3(get, set)]
    pub geography_id: Option<String>,
    #[pyo3(get, set)]
    pub palette_state: String,
    #[pyo3(get, set)]
    pub emotional_state: Option<String>,
    #[pyo3(get, set)]
    pub lineage_state: Option<String>,
}

#[pymethods]
impl SceneState {
    #[new]
    #[pyo3(signature = (id, geography_id, palette_state, emotional_state, lineage_state))]
    pub fn new(
        id: String,
        geography_id: Option<String>,
        palette_state: String,
        emotional_state: Option<String>,
        lineage_state: Option<String>,
    ) -> Self {
        SceneState {
            id,
            geography_id,
            palette_state,
            emotional_state,
            lineage_state,
        }
    }
}

#[pyclass]
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub enum ContinuityRuleType {
    HardGeographyLock,
    PaletteArcPosition,
    EmotionalCausality,
    LineageIntegrity,
}

#[pyclass]
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EdgeRule {
    #[pyo3(get, set)]
    pub from_id: String,
    #[pyo3(get, set)]
    pub to_id: String,
    #[pyo3(get, set)]
    pub rule_type: ContinuityRuleType,
}

#[pymethods]
impl EdgeRule {
    #[new]
    pub fn new(from_id: String, to_id: String, rule_type: ContinuityRuleType) -> Self {
        EdgeRule {
            from_id,
            to_id,
            rule_type,
        }
    }
}
