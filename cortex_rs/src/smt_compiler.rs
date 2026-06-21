use crate::scene_model::{ContinuityRuleType, EdgeRule, SceneState};
use pyo3::prelude::*;
use z3::{SatResult, Solver};

#[pyclass]
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum GateStatus {
    Satisfied,
    Violated,
    Unspecified,
}

#[pyclass]
#[derive(Debug, Clone)]
pub struct Verdict {
    #[pyo3(get)]
    pub status: GateStatus,
    #[pyo3(get)]
    pub proof_trace: Vec<String>,
    #[pyo3(get)]
    pub unsat_core: Option<Vec<String>>,
    #[pyo3(get)]
    pub entropy_hash: Option<String>,
}

#[pymethods]
impl Verdict {
    #[new]
    pub fn new(
        status: GateStatus,
        proof_trace: Vec<String>,
        unsat_core: Option<Vec<String>>,
        entropy_hash: Option<String>,
    ) -> Self {
        Verdict {
            status,
            proof_trace,
            unsat_core,
            entropy_hash,
        }
    }
}

pub fn continuity_rule_to_z3(
    rule: &EdgeRule,
    from: &SceneState,
    to: &SceneState,
) -> (z3::ast::Bool, String) {
    match rule.rule_type {
        ContinuityRuleType::HardGeographyLock => {
            let from_geo = from.geography_id.as_deref().unwrap_or("");
            let to_geo = to.geography_id.as_deref().unwrap_or("");
            let is_match = !from_geo.is_empty() && from_geo == to_geo;

            let constraint = z3::ast::Bool::from_bool(is_match);
            (
                constraint,
                format!("HardGeographyLock({}->{})", rule.from_id, rule.to_id),
            )
        }
        ContinuityRuleType::PaletteArcPosition => {
            let is_valid = !from.palette_state.is_empty() && !to.palette_state.is_empty();
            let constraint = z3::ast::Bool::from_bool(is_valid);
            (
                constraint,
                format!("PaletteArcPosition({}->{})", rule.from_id, rule.to_id),
            )
        }
        ContinuityRuleType::EmotionalCausality => {
            let from_emo = from.emotional_state.as_deref().unwrap_or("");
            let to_emo = to.emotional_state.as_deref().unwrap_or("");
            let is_valid = !from_emo.is_empty() && !to_emo.is_empty();
            let constraint = z3::ast::Bool::from_bool(is_valid);
            (
                constraint,
                format!("EmotionalCausality({}->{})", rule.from_id, rule.to_id),
            )
        }
        ContinuityRuleType::LineageIntegrity => {
            let from_lin = from.lineage_state.as_deref().unwrap_or("");
            let to_lin = to.lineage_state.as_deref().unwrap_or("");
            let is_valid = from_lin == to_lin && !from_lin.is_empty();
            let constraint = z3::ast::Bool::from_bool(is_valid);
            (
                constraint,
                format!("LineageIntegrity({}->{})", rule.from_id, rule.to_id),
            )
        }
    }
}

#[pyfunction]
pub fn validate_scene_transition(
    from_state: &SceneState,
    to_state: &SceneState,
    rules: Vec<EdgeRule>,
) -> Verdict {
    if rules.is_empty() {
        return Verdict {
            status: GateStatus::Unspecified,
            proof_trace: vec![],
            unsat_core: None,
            entropy_hash: None,
        };
    }

    // z3 0.20 uses a thread-local context, so we just instantiate a solver directly
    let solver = Solver::new();

    let mut trace = Vec::new();

    for rule in rules {
        let (ast, name) = continuity_rule_to_z3(&rule, from_state, to_state);
        // Using assert_and_track for UNSAT core extraction
        let z3_name = z3::ast::Bool::new_const(name.clone());
        solver.assert_and_track(&ast, &z3_name);
        trace.push(name);
    }

    match solver.check() {
        SatResult::Sat => Verdict {
            status: GateStatus::Satisfied,
            proof_trace: trace,
            unsat_core: None,
            entropy_hash: None,
        },
        SatResult::Unsat => {
            let core = solver.get_unsat_core();
            let core_names: Vec<String> = core
                .iter()
                .map(|ast| ast.to_string().replace('|', ""))
                .collect();
            Verdict {
                status: GateStatus::Violated,
                proof_trace: trace,
                unsat_core: Some(core_names),
                entropy_hash: None,
            }
        }
        SatResult::Unknown => Verdict {
            status: GateStatus::Violated,
            proof_trace: trace,
            unsat_core: Some(vec!["Z3 Unknown result".to_string()]),
            entropy_hash: None,
        },
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_unspecified_empty_spec() {
        let from = SceneState::new("1".into(), Some("geo_a".into()), "warm".into(), None, None);
        let to = SceneState::new("2".into(), Some("geo_b".into()), "cold".into(), None, None);
        let verdict = validate_scene_transition(&from, &to, vec![]);
        assert_eq!(verdict.status, GateStatus::Unspecified);
    }

    #[test]
    fn test_satisfied_spec() {
        let from = SceneState::new("1".into(), Some("geo_a".into()), "warm".into(), None, None);
        let to = SceneState::new("2".into(), Some("geo_a".into()), "cold".into(), None, None);
        let rule = EdgeRule::new(
            "1".into(),
            "2".into(),
            ContinuityRuleType::HardGeographyLock,
        );
        let verdict = validate_scene_transition(&from, &to, vec![rule]);
        assert_eq!(verdict.status, GateStatus::Satisfied);
    }

    #[test]
    fn test_violated_spec() {
        let from = SceneState::new("1".into(), Some("geo_a".into()), "warm".into(), None, None);
        let to = SceneState::new("2".into(), Some("geo_b".into()), "cold".into(), None, None);
        let rule = EdgeRule::new(
            "1".into(),
            "2".into(),
            ContinuityRuleType::HardGeographyLock,
        );
        let verdict = validate_scene_transition(&from, &to, vec![rule]);
        assert_eq!(verdict.status, GateStatus::Violated);
        assert!(verdict.unsat_core.is_some());
        assert_eq!(verdict.unsat_core.unwrap()[0], "HardGeographyLock(1->2)");
    }
}
