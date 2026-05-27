//! CORTEX PyO3 Bridge — Exposes Inverse AlphaProof Engine to Python
//!
//! Wraps the Rust-native inverse engine pipeline into Python-callable
//! classes. Zero-copy where possible, serde_json for structured data.
//!
//! Exposed classes:
//!   - PyDeductionDAG     → traceback module
//!   - PyCurriculumEngine → curriculum module
//!   - PyConjecturer      → conjecturer module
//!   - PyInverseEngine    → unified pipeline
//!
//! Reality Level: C5-REAL

use pyo3::prelude::*;
use pyo3::exceptions::PyRuntimeError;

use crate::traceback::{DeductionDAG, DeductionRule};
use crate::curriculum::CurriculumEngine;
use crate::conjecturer::{EvolutionaryConjecturer, MutationOp};
use crate::inverse_engine::{InverseEngine, InverseConfig, ThresholdSolver, DifficultyThresholdSolver};

// ─────────────────────────────────────────────────────────────
// §1 — PyDeductionDAG
// ─────────────────────────────────────────────────────────────

#[pyclass(name = "DeductionDAG")]
pub struct PyDeductionDAG {
    inner: DeductionDAG,
}

#[pymethods]
impl PyDeductionDAG {
    #[new]
    pub fn new() -> Self {
        PyDeductionDAG { inner: DeductionDAG::new() }
    }

    /// Add an axiom (premise). Returns the fact ID.
    pub fn add_axiom(&mut self, content: String) -> u64 {
        self.inner.add_axiom(content)
    }

    /// Add an auxiliary construction. Returns the fact ID.
    pub fn add_auxiliary(&mut self, content: String) -> u64 {
        self.inner.add_auxiliary(content)
    }

    /// Add a deduction rule.
    pub fn add_rule(&mut self, name: String, arity: usize, input_pattern: Vec<String>, output_template: String) {
        self.inner.add_rule(DeductionRule {
            name,
            arity,
            input_pattern,
            output_template,
        });
    }

    /// Derive a new fact from existing facts. Returns fact ID or None.
    pub fn derive(&mut self, content: String, premises: Vec<u64>, rule_name: String) -> Option<u64> {
        self.inner.derive(content, premises, rule_name)
    }

    /// Exhaustively apply all rules up to max_depth. Returns count of new facts.
    pub fn deduce_exhaustive(&mut self, max_depth: u32) -> usize {
        self.inner.deduce_exhaustive(max_depth)
    }

    /// Traceback from a conclusion. Returns JSON string of TracebackResult.
    pub fn traceback(&self, conclusion_id: u64) -> PyResult<String> {
        match self.inner.traceback(conclusion_id) {
            Some(result) => serde_json::to_string(&result)
                .map_err(|e| PyRuntimeError::new_err(format!("Serialize error: {}", e))),
            None => Err(PyRuntimeError::new_err("Fact not found")),
        }
    }

    /// Generate synthetic training triples. Returns JSON array.
    pub fn generate_synthetic_triples(&self) -> PyResult<String> {
        let triples = self.inner.generate_synthetic_triples();
        serde_json::to_string(&triples)
            .map_err(|e| PyRuntimeError::new_err(format!("Serialize error: {}", e)))
    }

    /// Number of facts in the DAG.
    pub fn fact_count(&self) -> usize {
        self.inner.fact_count()
    }

    /// Number of axioms.
    pub fn axiom_count(&self) -> usize {
        self.inner.axiom_count()
    }

    /// Maximum derivation depth.
    pub fn max_depth(&self) -> u32 {
        self.inner.max_depth()
    }

    /// Number of derived facts.
    pub fn derived_count(&self) -> usize {
        self.inner.derived_count()
    }

    /// Get fact content by ID. Returns JSON string.
    pub fn get_fact(&self, id: u64) -> PyResult<String> {
        match self.inner.get_fact(id) {
            Some(fact) => serde_json::to_string(fact)
                .map_err(|e| PyRuntimeError::new_err(format!("Serialize error: {}", e))),
            None => Err(PyRuntimeError::new_err("Fact not found")),
        }
    }
}

// ─────────────────────────────────────────────────────────────
// §2 — PyCurriculumEngine
// ─────────────────────────────────────────────────────────────

#[pyclass(name = "CurriculumEngine")]
pub struct PyCurriculumEngine {
    inner: CurriculumEngine,
}

#[pymethods]
impl PyCurriculumEngine {
    #[new]
    pub fn new() -> Self {
        PyCurriculumEngine { inner: CurriculumEngine::new() }
    }

    /// Set the target problem. Returns hex-encoded problem ID.
    pub fn set_target(&mut self, premises: Vec<String>, goal: String, difficulty: f64) -> String {
        let id = self.inner.set_target(premises, goal, difficulty);
        hex::encode(id)
    }

    /// Add a substitution pair for the specialization operator.
    pub fn add_substitution(&mut self, from: String, to: String) {
        self.inner.add_substitution(from, to);
    }

    /// Generate N levels of curriculum. Returns count of new variants.
    pub fn generate(&mut self, depth: u32) -> usize {
        self.inner.generate(depth)
    }

    /// Decompose target into subgoals. Returns list of hex problem IDs.
    pub fn decompose_target(&mut self, subgoals: Vec<String>) -> Vec<String> {
        self.inner.decompose_target(subgoals)
            .into_iter()
            .map(hex::encode)
            .collect()
    }

    /// Generate analogues. Returns list of hex problem IDs.
    pub fn analogize_target(&mut self, swaps: Vec<(String, String)>) -> Vec<String> {
        self.inner.analogize_target(swaps)
            .into_iter()
            .map(hex::encode)
            .collect()
    }

    /// Mark a problem as solved (by hex ID).
    pub fn mark_solved(&mut self, hex_id: &str, proof_steps: Vec<String>, time_us: u64) -> PyResult<()> {
        let id = hex_to_id(hex_id)?;
        self.inner.mark_solved(&id, proof_steps, time_us);
        Ok(())
    }

    /// Get the next best problem to attempt. Returns JSON or None.
    pub fn next_problem(&self) -> Option<String> {
        self.inner.next_problem()
            .and_then(|p| serde_json::to_string(p).ok())
    }

    /// Get curriculum statistics as JSON.
    pub fn stats(&self) -> PyResult<String> {
        let s = self.inner.stats();
        serde_json::to_string(&s)
            .map_err(|e| PyRuntimeError::new_err(format!("Serialize error: {}", e)))
    }

    /// Total number of nodes.
    pub fn len(&self) -> usize {
        self.inner.len()
    }

    /// Whether the target is solved.
    pub fn is_target_solved(&self) -> bool {
        self.inner.is_target_solved()
    }

    /// Solve rate (fraction solved).
    pub fn solve_rate(&self) -> f64 {
        self.inner.solve_rate()
    }
}

// ─────────────────────────────────────────────────────────────
// §3 — PyConjecturer
// ─────────────────────────────────────────────────────────────

#[pyclass(name = "EvolutionaryConjecturer")]
pub struct PyConjecturer {
    inner: EvolutionaryConjecturer,
}

#[pymethods]
impl PyConjecturer {
    #[new]
    #[pyo3(signature = (max_population=200))]
    pub fn new(max_population: usize) -> Self {
        PyConjecturer {
            inner: EvolutionaryConjecturer::new(max_population),
        }
    }

    /// Seed a conjecture. Returns hex ID.
    pub fn seed(&mut self, premises: Vec<String>, conclusion: String, elo: f64) -> String {
        let id = self.inner.seed(premises, conclusion, elo);
        hex::encode(id)
    }

    /// Add a negate mutation.
    pub fn add_negate_mutation(&mut self) {
        self.inner.add_mutation(MutationOp::Negate);
    }

    /// Add an add-premise mutation.
    pub fn add_premise_mutation(&mut self, premise: String) {
        self.inner.add_mutation(MutationOp::AddPremise(premise));
    }

    /// Add a generalize mutation.
    pub fn add_generalize_mutation(&mut self, from: String, to: String) {
        self.inner.add_mutation(MutationOp::Generalize { from, to });
    }

    /// Add a specialize mutation.
    pub fn add_specialize_mutation(&mut self, from: String, to: String) {
        self.inner.add_mutation(MutationOp::Specialize { from, to });
    }

    /// Add a swap mutation.
    pub fn add_swap_mutation(&mut self, a: String, b: String) {
        self.inner.add_mutation(MutationOp::Swap { a, b });
    }

    /// Add a compose mutation.
    pub fn add_compose_mutation(&mut self, extra: String) {
        self.inner.add_mutation(MutationOp::Compose(extra));
    }

    /// Run one evolution cycle. Returns JSON stats.
    pub fn evolve(&mut self) -> PyResult<String> {
        let stats = self.inner.evolve();
        serde_json::to_string(&stats)
            .map_err(|e| PyRuntimeError::new_err(format!("Serialize error: {}", e)))
    }

    /// Mark a conjecture as proven (hex ID).
    pub fn mark_proven(&mut self, hex_id: &str) -> PyResult<()> {
        let id = hex_to_id(hex_id)?;
        self.inner.mark_proven(&id, [0u8; 32]);
        Ok(())
    }

    /// Mark a conjecture as refuted (hex ID).
    pub fn mark_refuted(&mut self, hex_id: &str, counterexample: String) -> PyResult<()> {
        let id = hex_to_id(hex_id)?;
        self.inner.mark_refuted(&id, counterexample);
        Ok(())
    }

    /// Mark a conjecture as surviving a proof attempt.
    pub fn mark_surviving(&mut self, hex_id: &str) -> PyResult<()> {
        let id = hex_to_id(hex_id)?;
        self.inner.mark_surviving(&id);
        Ok(())
    }

    /// Get top N conjectures by Elo. Returns JSON array.
    pub fn top_conjectures(&self, n: usize) -> PyResult<String> {
        let top = self.inner.top_conjectures(n);
        serde_json::to_string(&top)
            .map_err(|e| PyRuntimeError::new_err(format!("Serialize error: {}", e)))
    }

    /// Population size.
    pub fn len(&self) -> usize {
        self.inner.len()
    }

    /// Count of surviving conjectures.
    pub fn surviving_count(&self) -> usize {
        self.inner.surviving_conjectures().len()
    }

    /// Count of proven conjectures.
    pub fn proven_count(&self) -> usize {
        self.inner.proven_conjectures().len()
    }
}

// ─────────────────────────────────────────────────────────────
// §4 — PyInverseEngine
// ─────────────────────────────────────────────────────────────

#[pyclass(name = "InverseEngine")]
pub struct PyInverseEngine {
    inner: InverseEngine,
}

#[pymethods]
impl PyInverseEngine {
    #[new]
    #[pyo3(signature = (
        conjecturer_population=200,
        evolution_cycles=3,
        curriculum_depth=4,
        traceback_max_depth=10,
        difficulty_threshold=0.3,
        batch_size=50
    ))]
    pub fn new(
        conjecturer_population: usize,
        evolution_cycles: u32,
        curriculum_depth: u32,
        traceback_max_depth: u32,
        difficulty_threshold: f64,
        batch_size: usize,
    ) -> Self {
        let config = InverseConfig {
            conjecturer_population,
            evolution_cycles,
            curriculum_depth,
            traceback_max_depth,
            difficulty_threshold,
            batch_size,
        };
        PyInverseEngine {
            inner: InverseEngine::new(config),
        }
    }

    /// Seed a conjecture into the pipeline.
    pub fn seed(&mut self, premises: Vec<String>, conclusion: String, elo: f64) {
        self.inner.seed(premises, conclusion, elo);
    }

    /// Add a negate mutation.
    pub fn add_negate_mutation(&mut self) {
        self.inner.add_mutation(MutationOp::Negate);
    }

    /// Add an add-premise mutation.
    pub fn add_premise_mutation(&mut self, premise: String) {
        self.inner.add_mutation(MutationOp::AddPremise(premise));
    }

    /// Add a generalize mutation.
    pub fn add_generalize_mutation(&mut self, from: String, to: String) {
        self.inner.add_mutation(MutationOp::Generalize { from, to });
    }

    /// Add a swap mutation.
    pub fn add_swap_mutation(&mut self, a: String, b: String) {
        self.inner.add_mutation(MutationOp::Swap { a, b });
    }

    /// Run one full pipeline iteration with threshold solver.
    /// Returns JSON telemetry.
    pub fn iterate_threshold(&mut self, max_premises: usize) -> PyResult<String> {
        let solver = ThresholdSolver { max_premises };
        let telemetry = self.inner.iterate(&solver);
        serde_json::to_string(&telemetry)
            .map_err(|e| PyRuntimeError::new_err(format!("Serialize error: {}", e)))
    }

    /// Run one full pipeline iteration with difficulty solver.
    /// Returns JSON telemetry.
    pub fn iterate_difficulty(&mut self, threshold: f64) -> PyResult<String> {
        let solver = DifficultyThresholdSolver { threshold };
        let telemetry = self.inner.iterate(&solver);
        serde_json::to_string(&telemetry)
            .map_err(|e| PyRuntimeError::new_err(format!("Serialize error: {}", e)))
    }

    /// Get all accumulated training data as JSON.
    pub fn training_data(&self) -> PyResult<String> {
        serde_json::to_string(self.inner.training_data())
            .map_err(|e| PyRuntimeError::new_err(format!("Serialize error: {}", e)))
    }

    /// Number of training triples.
    pub fn training_data_count(&self) -> usize {
        self.inner.training_data_count()
    }

    /// Current iteration.
    pub fn current_iteration(&self) -> u32 {
        self.inner.current_iteration()
    }

    /// Population size.
    pub fn population_size(&self) -> usize {
        self.inner.population_size()
    }

    /// Surviving conjectures count.
    pub fn surviving_count(&self) -> usize {
        self.inner.surviving_count()
    }

    /// Proven conjectures count.
    pub fn proven_count(&self) -> usize {
        self.inner.proven_count()
    }

    /// Full cumulative stats as JSON.
    pub fn cumulative_stats(&self) -> PyResult<String> {
        let stats = self.inner.cumulative_stats();
        serde_json::to_string(&stats)
            .map_err(|e| PyRuntimeError::new_err(format!("Serialize error: {}", e)))
    }

    /// Full telemetry history as JSON.
    pub fn telemetry(&self) -> PyResult<String> {
        serde_json::to_string(self.inner.telemetry())
            .map_err(|e| PyRuntimeError::new_err(format!("Serialize error: {}", e)))
    }
}

// ─────────────────────────────────────────────────────────────
// §5 — Helpers
// ─────────────────────────────────────────────────────────────

fn hex_to_id(hex_str: &str) -> PyResult<[u8; 32]> {
    let bytes = hex::decode(hex_str)
        .map_err(|e| PyRuntimeError::new_err(format!("Invalid hex: {}", e)))?;
    if bytes.len() != 32 {
        return Err(PyRuntimeError::new_err("ID must be 32 bytes (64 hex chars)"));
    }
    let mut id = [0u8; 32];
    id.copy_from_slice(&bytes);
    Ok(id)
}

/// Register all inverse engine classes into the PyO3 module.
pub fn register(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyDeductionDAG>()?;
    m.add_class::<PyCurriculumEngine>()?;
    m.add_class::<PyConjecturer>()?;
    m.add_class::<PyInverseEngine>()?;
    Ok(())
}
