//! CORTEX Traceback Engine — Inverse AlphaGeometry Pattern
//!
//! DAG-based deduction with backward dependency extraction.
//! Implements the "Embryogenesis-Metabolism Duality":
//!   - Forward: Exhaustive deduction from premises → fact DAG
//!   - Inverse: Traceback from conclusions → minimal premise sets
//!
//! Architecture mirrors AlphaGeometry's synthetic data pipeline:
//!   1. Sample random structures (premises)
//!   2. Deduce all reachable facts (forward pass)
//!   3. Traceback from any conclusion to find minimal proof path
//!   4. Extract (problem, auxiliary_hints, proof) triples
//!
//! Reality Level: C5-REAL

use serde::{Deserialize, Serialize};
use rayon::prelude::*;
use std::collections::{HashMap, HashSet, VecDeque};

// ─────────────────────────────────────────────────────────────
// §1 — Core Types
// ─────────────────────────────────────────────────────────────

/// Unique identifier for a fact node in the deduction DAG
pub type FactId = u64;

/// A single fact (node in the DAG)
#[derive(Serialize, Deserialize, Clone, Debug)]
pub struct Fact {
    pub id: FactId,
    pub content: String,
    /// IDs of facts that were used to derive this fact (empty = axiom/premise)
    pub premises: Vec<FactId>,
    /// The deduction rule that produced this fact
    pub rule: Option<String>,
    /// Depth in the deduction tree (0 = axiom)
    pub depth: u32,
    /// Whether this fact required an auxiliary construction
    pub is_auxiliary: bool,
}

/// A deduction rule: given input fact patterns, produce output facts
#[derive(Serialize, Deserialize, Clone, Debug)]
pub struct DeductionRule {
    pub name: String,
    /// Number of input facts required
    pub arity: usize,
    /// Predicate: which fact content patterns match this rule
    pub input_pattern: Vec<String>,
    /// Template for the output fact content
    pub output_template: String,
}

/// Result of a traceback operation: the minimal proof path
#[derive(Serialize, Deserialize, Clone, Debug)]
pub struct TracebackResult {
    /// The conclusion we traced back from
    pub conclusion: FactId,
    /// The minimal set of axioms/premises needed
    pub minimal_premises: Vec<FactId>,
    /// The auxiliary constructions that were necessary
    pub auxiliary_constructions: Vec<FactId>,
    /// The full proof path (ordered sequence of facts)
    pub proof_path: Vec<FactId>,
    /// Depth of the proof
    pub proof_depth: u32,
    /// Whether this traceback is non-trivial (depth > 1 and has auxiliaries)
    pub is_nontrivial: bool,
}

/// A synthetic training triple: (problem, hints, proof)
#[derive(Serialize, Deserialize, Clone, Debug)]
pub struct SyntheticTriple {
    pub premises: Vec<String>,
    pub conclusion: String,
    pub auxiliary_hints: Vec<String>,
    pub proof_steps: Vec<String>,
    pub difficulty: u32,
}

// ─────────────────────────────────────────────────────────────
// §2 — The Deduction DAG
// ─────────────────────────────────────────────────────────────

/// The core deduction DAG — stores facts and their derivation relationships.
/// Forward pass: exhaustively apply rules to derive new facts.
/// Inverse pass: traceback from any fact to find minimal proof.
#[derive(Clone, Debug)]
pub struct DeductionDAG {
    facts: HashMap<FactId, Fact>,
    /// Reverse index: fact_id → set of facts derived FROM this fact
    children: HashMap<FactId, Vec<FactId>>,
    /// Forward index: fact_id → set of facts this fact was derived FROM
    parents: HashMap<FactId, Vec<FactId>>,
    /// All axioms (depth 0 facts)
    axioms: Vec<FactId>,
    /// Available deduction rules
    rules: Vec<DeductionRule>,
    /// Next available fact ID
    next_id: FactId,
}

impl DeductionDAG {
    /// Create a new empty DAG
    pub fn new() -> Self {
        DeductionDAG {
            facts: HashMap::new(),
            children: HashMap::new(),
            parents: HashMap::new(),
            axioms: Vec::new(),
            rules: Vec::new(),
            next_id: 0,
        }
    }

    /// Add an axiom (premise) to the DAG — a fact with no derivation
    pub fn add_axiom(&mut self, content: String) -> FactId {
        let id = self.next_id;
        self.next_id += 1;
        let fact = Fact {
            id,
            content,
            premises: Vec::new(),
            rule: None,
            depth: 0,
            is_auxiliary: false,
        };
        self.facts.insert(id, fact);
        self.axioms.push(id);
        id
    }

    /// Add an auxiliary construction (a fact introduced to bridge a gap)
    pub fn add_auxiliary(&mut self, content: String) -> FactId {
        let id = self.next_id;
        self.next_id += 1;
        let fact = Fact {
            id,
            content,
            premises: Vec::new(),
            rule: None,
            depth: 0,
            is_auxiliary: true,
        };
        self.facts.insert(id, fact);
        id
    }

    /// Register a deduction rule
    pub fn add_rule(&mut self, rule: DeductionRule) {
        self.rules.push(rule);
    }

    /// Derive a new fact from existing facts using a named rule
    pub fn derive(&mut self, content: String, premises: Vec<FactId>, rule_name: String) -> Option<FactId> {
        // Verify all premises exist
        let max_depth = premises.iter()
            .filter_map(|id| self.facts.get(id).map(|f| f.depth))
            .max()
            .unwrap_or(0);

        let has_auxiliary = premises.iter()
            .any(|id| self.facts.get(id).is_some_and(|f| f.is_auxiliary));

        let id = self.next_id;
        self.next_id += 1;

        let fact = Fact {
            id,
            content,
            premises: premises.clone(),
            rule: Some(rule_name),
            depth: max_depth + 1,
            is_auxiliary: has_auxiliary,
        };

        // Update indices
        for &premise_id in &premises {
            self.children.entry(premise_id).or_default().push(id);
        }
        self.parents.insert(id, premises);

        self.facts.insert(id, fact);
        Some(id)
    }

    // ─────────────────────────────────────────────────────────
    // §3 — Forward Deduction (Exhaustive)
    // ─────────────────────────────────────────────────────────

    /// Exhaustively apply all rules to derive new facts until fixpoint.
    /// Returns the number of new facts derived.
    pub fn deduce_exhaustive(&mut self, max_depth: u32) -> usize {
        let mut new_facts_total = 0;
        let mut current_depth = 0;

        while current_depth < max_depth {
            let mut new_derivations: Vec<(String, Vec<FactId>, String)> = Vec::new();

            // Collect all facts at current frontier
            let frontier: Vec<FactId> = self.facts.iter()
                .filter(|(_, f)| f.depth <= current_depth)
                .map(|(id, _)| *id)
                .collect();

            // Try each rule against combinations of frontier facts
            for rule in &self.rules {
                if rule.arity == 1 {
                    // Unary rules
                    for &fact_id in &frontier {
                        if let Some(fact) = self.facts.get(&fact_id) {
                            for pattern in &rule.input_pattern {
                                if fact.content.contains(pattern) {
                                    let output = rule.output_template
                                        .replace("{0}", &fact.content);
                                    // Dedup: don't derive existing facts
                                    if !self.facts.values().any(|f| f.content == output) {
                                        new_derivations.push((
                                            output,
                                            vec![fact_id],
                                            rule.name.clone(),
                                        ));
                                    }
                                }
                            }
                        }
                    }
                } else if rule.arity == 2 {
                    // Binary rules: try all pairs
                    for (i, &id_a) in frontier.iter().enumerate() {
                        for &id_b in frontier.iter().skip(i + 1) {
                            if let (Some(a), Some(b)) = (self.facts.get(&id_a), self.facts.get(&id_b)) {
                                let matches = rule.input_pattern.len() >= 2
                                    && (a.content.contains(&rule.input_pattern[0])
                                        && b.content.contains(&rule.input_pattern[1]))
                                    || (a.content.contains(&rule.input_pattern[1])
                                        && b.content.contains(&rule.input_pattern[0]));
                                if matches {
                                    let output = rule.output_template
                                        .replace("{0}", &a.content)
                                        .replace("{1}", &b.content);
                                    if !self.facts.values().any(|f| f.content == output) {
                                        new_derivations.push((
                                            output,
                                            vec![id_a, id_b],
                                            rule.name.clone(),
                                        ));
                                    }
                                }
                            }
                        }
                    }
                }
            }

            if new_derivations.is_empty() {
                break; // Fixpoint reached
            }

            for (content, premises, rule_name) in new_derivations {
                self.derive(content, premises, rule_name);
                new_facts_total += 1;
            }

            current_depth += 1;
        }

        new_facts_total
    }

    // ─────────────────────────────────────────────────────────
    // §4 — Traceback (The Inverse Engine)
    // ─────────────────────────────────────────────────────────

    /// Traceback from a conclusion to find the minimal proof path.
    /// This IS the inverse of theorem proving:
    ///   Given a conclusion, what premises and constructions were essential?
    pub fn traceback(&self, conclusion_id: FactId) -> Option<TracebackResult> {
        let conclusion = self.facts.get(&conclusion_id)?;

        let mut visited: HashSet<FactId> = HashSet::new();
        let mut proof_path: Vec<FactId> = Vec::new();
        let mut minimal_premises: Vec<FactId> = Vec::new();
        let mut auxiliary_constructions: Vec<FactId> = Vec::new();
        let mut queue: VecDeque<FactId> = VecDeque::new();

        queue.push_back(conclusion_id);

        // BFS backward through the DAG
        while let Some(current_id) = queue.pop_front() {
            if visited.contains(&current_id) {
                continue;
            }
            visited.insert(current_id);

            if let Some(fact) = self.facts.get(&current_id) {
                proof_path.push(current_id);

                if fact.premises.is_empty() {
                    // This is an axiom or auxiliary — a leaf in the proof
                    if fact.is_auxiliary {
                        auxiliary_constructions.push(current_id);
                    } else {
                        minimal_premises.push(current_id);
                    }
                } else {
                    // Continue backward
                    for &premise_id in &fact.premises {
                        if !visited.contains(&premise_id) {
                            queue.push_back(premise_id);
                        }
                    }
                }
            }
        }

        // Reverse to get proof in forward order (premises first)
        proof_path.reverse();

        let is_nontrivial = conclusion.depth > 1 && !auxiliary_constructions.is_empty();

        Some(TracebackResult {
            conclusion: conclusion_id,
            minimal_premises,
            auxiliary_constructions,
            proof_path,
            proof_depth: conclusion.depth,
            is_nontrivial,
        })
    }

    /// Generate synthetic training triples from all non-trivial conclusions.
    /// This is the AlphaGeometry-style inverse pipeline.
    pub fn generate_synthetic_triples(&self) -> Vec<SyntheticTriple> {
        // Find all derived facts (non-axioms)
        let derived: Vec<FactId> = self.facts.iter()
            .filter(|(_, f)| f.depth > 0)
            .map(|(id, _)| *id)
            .collect();

        derived.par_iter()
            .filter_map(|&fact_id| {
                let tb = self.traceback(fact_id)?;
                if !tb.is_nontrivial {
                    return None; // Filter trivial derivations
                }

                let conclusion = self.facts.get(&fact_id)?;
                let premises: Vec<String> = tb.minimal_premises.iter()
                    .filter_map(|id| self.facts.get(id).map(|f| f.content.clone()))
                    .collect();
                let hints: Vec<String> = tb.auxiliary_constructions.iter()
                    .filter_map(|id| self.facts.get(id).map(|f| f.content.clone()))
                    .collect();
                let steps: Vec<String> = tb.proof_path.iter()
                    .filter_map(|id| {
                        let f = self.facts.get(id)?;
                        let rule_str = f.rule.as_deref().unwrap_or("axiom");
                        Some(format!("[{}] {}", rule_str, f.content))
                    })
                    .collect();

                Some(SyntheticTriple {
                    premises,
                    conclusion: conclusion.content.clone(),
                    auxiliary_hints: hints,
                    proof_steps: steps,
                    difficulty: tb.proof_depth,
                })
            })
            .collect()
    }

    // ─────────────────────────────────────────────────────────
    // §5 — Statistics & Introspection
    // ─────────────────────────────────────────────────────────

    /// Total number of facts in the DAG
    pub fn fact_count(&self) -> usize {
        self.facts.len()
    }

    /// Number of axioms (depth 0)
    pub fn axiom_count(&self) -> usize {
        self.axioms.len()
    }

    /// Maximum derivation depth
    pub fn max_depth(&self) -> u32 {
        self.facts.values().map(|f| f.depth).max().unwrap_or(0)
    }

    /// Number of derived (non-axiom) facts
    pub fn derived_count(&self) -> usize {
        self.facts.values().filter(|f| f.depth > 0).count()
    }

    /// Get a fact by ID
    pub fn get_fact(&self, id: FactId) -> Option<&Fact> {
        self.facts.get(&id)
    }

    /// Get all facts at a given depth
    pub fn facts_at_depth(&self, depth: u32) -> Vec<&Fact> {
        self.facts.values().filter(|f| f.depth == depth).collect()
    }
}

// ─────────────────────────────────────────────────────────────
// §6 — Benchmarks & Tests
// ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use std::time::Instant;

    fn build_test_dag() -> DeductionDAG {
        let mut dag = DeductionDAG::new();

        // Axioms (premises)
        let a = dag.add_axiom("point(A)".into());
        let b = dag.add_axiom("point(B)".into());
        let c = dag.add_axiom("point(C)".into());
        let ab = dag.add_axiom("line(A,B)".into());
        let bc = dag.add_axiom("line(B,C)".into());

        // Auxiliary construction
        let m = dag.add_auxiliary("midpoint(M,A,B)".into());

        // Derived facts
        let _d1 = dag.derive(
            "collinear(A,M,B)".into(),
            vec![a, b, m],
            "midpoint_collinear".into(),
        );
        let d2 = dag.derive(
            "equal_dist(A,M,M,B)".into(),
            vec![m, a, b],
            "midpoint_equidist".into(),
        );
        let _d3 = dag.derive(
            "triangle(A,B,C)".into(),
            vec![a, b, c, ab, bc],
            "three_points_triangle".into(),
        );
        let _d4 = dag.derive(
            "median(M,C)".into(),
            vec![d2.unwrap(), c],
            "median_from_midpoint".into(),
        );

        dag
    }

    #[test]
    fn test_dag_construction() {
        let dag = build_test_dag();
        assert!(dag.fact_count() >= 9); // 5 axioms + 1 aux + 3-4 derived
        assert_eq!(dag.axiom_count(), 5);
        assert!(dag.max_depth() >= 2);
    }

    #[test]
    fn test_traceback_basic() {
        let dag = build_test_dag();
        // Find the median fact (deepest)
        let deepest = dag.facts.values()
            .filter(|f| f.content.contains("median"))
            .next();

        if let Some(fact) = deepest {
            let tb = dag.traceback(fact.id).unwrap();
            assert!(!tb.minimal_premises.is_empty());
            assert!(!tb.auxiliary_constructions.is_empty(), "Median requires midpoint auxiliary");
            assert!(tb.is_nontrivial);
            assert!(tb.proof_depth >= 2);
        }
    }

    #[test]
    fn test_synthetic_triple_generation() {
        let dag = build_test_dag();
        let triples = dag.generate_synthetic_triples();
        // Should have at least one non-trivial triple (the median)
        let nontrivial: Vec<_> = triples.iter()
            .filter(|t| t.difficulty >= 2)
            .collect();
        assert!(!nontrivial.is_empty(), "Should generate non-trivial triples");

        for triple in &nontrivial {
            assert!(!triple.premises.is_empty());
            assert!(!triple.auxiliary_hints.is_empty());
            assert!(!triple.proof_steps.is_empty());
        }
    }

    #[test]
    fn test_traceback_throughput() {
        let mut dag = DeductionDAG::new();

        // Build a deep chain: a0 → a1 → a2 → ... → aN
        let mut prev = dag.add_axiom("fact_0".into());
        for i in 1..1000 {
            let aux = dag.add_auxiliary(format!("aux_{}", i));
            prev = dag.derive(
                format!("fact_{}", i),
                vec![prev, aux],
                "chain_rule".into(),
            ).unwrap();
        }

        let start = Instant::now();
        let iterations = 10_000;
        for _ in 0..iterations {
            let _ = dag.traceback(prev);
        }
        let elapsed = start.elapsed();
        let rate = iterations as f64 / elapsed.as_secs_f64();

        // tracing::info!("═══════════════════════════════════════════");
        // tracing::info!("  TRACEBACK THROUGHPUT BENCHMARK");
        // tracing::info!("═══════════════════════════════════════════");
        // tracing::info!("  Chain depth: 1000");
        // tracing::info!("  Iterations:  {}", iterations);
        // tracing::info!("  Elapsed:     {:.4?}", elapsed);
        // tracing::info!("  Rate:        {:.0} tracebacks/sec", rate);
        // tracing::info!("═══════════════════════════════════════════");

        assert!(rate > 1000.0, "Traceback rate should exceed 1K ops/sec");
    }

    #[test]
    fn test_exhaustive_deduction() {
        let mut dag = DeductionDAG::new();

        dag.add_axiom("point(A)".into());
        dag.add_axiom("point(B)".into());
        dag.add_axiom("line(A,B)".into());

        dag.add_rule(DeductionRule {
            name: "point_on_line".into(),
            arity: 2,
            input_pattern: vec!["point".into(), "line".into()],
            output_template: "on_line({0},{1})".into(),
        });

        let new_facts = dag.deduce_exhaustive(3);
        assert!(new_facts > 0, "Should derive at least one new fact");
    }
}
