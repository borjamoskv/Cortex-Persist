//! CORTEX Evolutionary Conjecturer — AlphaProof Nexus Pattern
//!
//! Population-based conjecture discovery with Elo ranking.
//! Implements the multi-agent evolutionary architecture from
//! AlphaProof Nexus (May 2026):
//!
//!   1. Population: A pool of conjecture sketches
//!   2. Mutation: Structural transformations on formal statements
//!   3. Crossover: Combine premises/goals from different conjectures
//!   4. Selection: Elo-ranked tournament selection
//!   5. Verification: Formal proof attempts filter surviving conjectures
//!
//! The conjecturer IS the inverse of the prover:
//!   Prover:      Problem → Proof  (consumes uncertainty)
//!   Conjecturer: Structure → Problem  (generates uncertainty)
//!
//! Reality Level: C5-REAL

use serde::{Deserialize, Serialize};

use sha2::{Digest, Sha256};
use std::collections::HashMap;
use std::time::Instant;

// ─────────────────────────────────────────────────────────────
// §1 — Core Types
// ─────────────────────────────────────────────────────────────

pub type ConjectureId = [u8; 32];

/// A conjecture: an unproven formal statement
#[derive(Serialize, Deserialize, Clone, Debug)]
pub struct Conjecture {
    pub id: ConjectureId,
    /// Premises (hypotheses)
    pub premises: Vec<String>,
    /// The conjectured conclusion
    pub conclusion: String,
    /// Elo rating (higher = harder/more interesting)
    pub elo: f64,
    /// Generation number (0 = seed, increments per evolution cycle)
    pub generation: u32,
    /// How this conjecture was created
    pub origin: ConjectureOrigin,
    /// Verification status
    pub status: VerificationStatus,
    /// Number of failed counterexample attempts (higher = more likely true)
    pub survived_attacks: u32,
}

#[derive(Serialize, Deserialize, Clone, Debug)]
pub enum ConjectureOrigin {
    /// Manually seeded
    Seed,
    /// Created by mutating an existing conjecture
    Mutation { parent: ConjectureId, operator: String },
    /// Created by crossing two conjectures
    Crossover { parent_a: ConjectureId, parent_b: ConjectureId },
    /// Created by the traceback inverse engine
    Traceback { source_dag: String },
}

#[derive(Serialize, Deserialize, Clone, Debug, PartialEq)]
pub enum VerificationStatus {
    /// Not yet attempted
    Unverified,
    /// Proven true (with proof)
    Proven { proof_hash: [u8; 32] },
    /// Disproven by counterexample
    Refuted { counterexample: String },
    /// Proof attempted but timed out (still alive)
    Surviving,
    /// Marked as trivial (provable in 1 step)
    Trivial,
}

// ─────────────────────────────────────────────────────────────
// §2 — Mutation Operators
// ─────────────────────────────────────────────────────────────

/// Structural mutations on conjectures
#[derive(Serialize, Deserialize, Clone, Debug)]
pub enum MutationOp {
    /// Strengthen: add a premise
    AddPremise(String),
    /// Weaken: remove a premise
    RemovePremise(usize),
    /// Generalize: replace a specific term with a variable
    Generalize { from: String, to: String },
    /// Specialize: replace a variable with a specific term
    Specialize { from: String, to: String },
    /// Negate: flip the conclusion
    Negate,
    /// Swap: exchange two terms throughout
    Swap { a: String, b: String },
    /// Compose: chain two conclusions
    Compose(String),
}

fn hash_conjecture(premises: &[String], conclusion: &str) -> ConjectureId {
    let mut hasher = Sha256::new();
    let mut sorted_premises = premises.to_vec();
    sorted_premises.sort(); // Canonical ordering for dedup
    for p in &sorted_premises {
        hasher.update(p.as_bytes());
        hasher.update(b"|");
    }
    hasher.update("⊢".as_bytes());
    hasher.update(conclusion.as_bytes());
    let result = hasher.finalize();
    let mut id = [0u8; 32];
    id.copy_from_slice(&result);
    id
}

fn apply_mutation(conjecture: &Conjecture, op: &MutationOp) -> Option<Conjecture> {
    let mut new_premises = conjecture.premises.clone();
    let mut new_conclusion = conjecture.conclusion.clone();

    match op {
        MutationOp::AddPremise(premise) => {
            if !new_premises.contains(premise) {
                new_premises.push(premise.clone());
            } else {
                return None; // Already present
            }
        }
        MutationOp::RemovePremise(idx) => {
            if *idx < new_premises.len() && new_premises.len() > 1 {
                new_premises.remove(*idx);
            } else {
                return None;
            }
        }
        MutationOp::Generalize { from, to } => {
            new_premises = new_premises.iter()
                .map(|p| p.replace(from.as_str(), to.as_str()))
                .collect();
            new_conclusion = new_conclusion.replace(from.as_str(), to.as_str());
        }
        MutationOp::Specialize { from, to } => {
            new_premises = new_premises.iter()
                .map(|p| p.replace(from.as_str(), to.as_str()))
                .collect();
            new_conclusion = new_conclusion.replace(from.as_str(), to.as_str());
        }
        MutationOp::Negate => {
            new_conclusion = if new_conclusion.starts_with("¬") {
                new_conclusion[2..].to_string() // Remove ¬
            } else {
                format!("¬{}", new_conclusion)
            };
        }
        MutationOp::Swap { a, b } => {
            let placeholder = "§§PLACEHOLDER§§";
            new_premises = new_premises.iter()
                .map(|p| {
                    p.replace(a.as_str(), placeholder)
                     .replace(b.as_str(), a.as_str())
                     .replace(placeholder, b.as_str())
                })
                .collect();
            new_conclusion = new_conclusion
                .replace(a.as_str(), placeholder)
                .replace(b.as_str(), a.as_str())
                .replace(placeholder, b.as_str());
        }
        MutationOp::Compose(extra_conclusion) => {
            new_conclusion = format!("{} ∧ {}", new_conclusion, extra_conclusion);
        }
    }

    let id = hash_conjecture(&new_premises, &new_conclusion);
    Some(Conjecture {
        id,
        premises: new_premises,
        conclusion: new_conclusion,
        elo: conjecture.elo,
        generation: conjecture.generation + 1,
        origin: ConjectureOrigin::Mutation {
            parent: conjecture.id,
            operator: format!("{:?}", op),
        },
        status: VerificationStatus::Unverified,
        survived_attacks: 0,
    })
}

// ─────────────────────────────────────────────────────────────
// §3 — Crossover
// ─────────────────────────────────────────────────────────────

fn crossover(a: &Conjecture, b: &Conjecture) -> Vec<Conjecture> {
    let mut results = Vec::new();

    // Type 1: Premises of A + Conclusion of B
    {
        let id = hash_conjecture(&a.premises, &b.conclusion);
        results.push(Conjecture {
            id,
            premises: a.premises.clone(),
            conclusion: b.conclusion.clone(),
            elo: (a.elo + b.elo) / 2.0,
            generation: a.generation.max(b.generation) + 1,
            origin: ConjectureOrigin::Crossover {
                parent_a: a.id,
                parent_b: b.id,
            },
            status: VerificationStatus::Unverified,
            survived_attacks: 0,
        });
    }

    // Type 2: Union of premises + conjunction of conclusions
    {
        let mut merged_premises = a.premises.clone();
        for p in &b.premises {
            if !merged_premises.contains(p) {
                merged_premises.push(p.clone());
            }
        }
        let merged_conclusion = format!("{} ∧ {}", a.conclusion, b.conclusion);
        let id = hash_conjecture(&merged_premises, &merged_conclusion);
        results.push(Conjecture {
            id,
            premises: merged_premises,
            conclusion: merged_conclusion,
            elo: (a.elo + b.elo) / 2.0 + 100.0, // Harder than parents
            generation: a.generation.max(b.generation) + 1,
            origin: ConjectureOrigin::Crossover {
                parent_a: a.id,
                parent_b: b.id,
            },
            status: VerificationStatus::Unverified,
            survived_attacks: 0,
        });
    }

    results
}

// ─────────────────────────────────────────────────────────────
// §4 — The Evolutionary Engine
// ─────────────────────────────────────────────────────────────

/// The Evolutionary Conjecturer: maintains a population of
/// conjectures and evolves them through mutation, crossover,
/// and Elo-based selection.
pub struct EvolutionaryConjecturer {
    population: HashMap<ConjectureId, Conjecture>,
    /// Available mutation operators
    mutation_pool: Vec<MutationOp>,
    /// Maximum population size
    max_population: usize,
    /// Current generation
    generation: u32,
}

impl EvolutionaryConjecturer {
    pub fn new(max_population: usize) -> Self {
        EvolutionaryConjecturer {
            population: HashMap::new(),
            mutation_pool: Vec::new(),
            max_population,
            generation: 0,
        }
    }

    /// Seed the population with an initial conjecture
    pub fn seed(&mut self, premises: Vec<String>, conclusion: String, elo: f64) -> ConjectureId {
        let id = hash_conjecture(&premises, &conclusion);
        let conjecture = Conjecture {
            id,
            premises,
            conclusion,
            elo,
            generation: 0,
            origin: ConjectureOrigin::Seed,
            status: VerificationStatus::Unverified,
            survived_attacks: 0,
        };
        self.population.insert(id, conjecture);
        id
    }

    /// Add a mutation operator to the pool
    pub fn add_mutation(&mut self, op: MutationOp) {
        self.mutation_pool.push(op);
    }

    /// Run one evolution cycle: mutate + crossover + select
    pub fn evolve(&mut self) -> EvolutionStats {
        let start = Instant::now();
        self.generation += 1;

        let mut new_conjectures: Vec<Conjecture> = Vec::new();

        // Phase 1: Mutation — apply each operator to each surviving conjecture
        let survivors: Vec<Conjecture> = self.population.values()
            .filter(|c| c.status != VerificationStatus::Trivial
                     && !matches!(c.status, VerificationStatus::Refuted { .. }))
            .cloned()
            .collect();

        for conjecture in &survivors {
            for op in &self.mutation_pool {
                if let Some(mutant) = apply_mutation(conjecture, op) {
                    if !self.population.contains_key(&mutant.id)
                        && !new_conjectures.iter().any(|c| c.id == mutant.id) {
                        new_conjectures.push(mutant);
                    }
                }
            }
        }

        // Phase 2: Crossover — pair top-Elo conjectures
        let mut ranked: Vec<&Conjecture> = survivors.iter().collect();
        ranked.sort_by(|a, b| b.elo.partial_cmp(&a.elo).unwrap_or(std::cmp::Ordering::Equal));

        let top_n = ranked.len().min(10);
        for i in 0..top_n {
            for j in (i + 1)..top_n {
                let children = crossover(ranked[i], ranked[j]);
                for child in children {
                    if !self.population.contains_key(&child.id)
                        && !new_conjectures.iter().any(|c| c.id == child.id) {
                        new_conjectures.push(child);
                    }
                }
            }
        }

        let mutations_generated = new_conjectures.len();

        // Phase 3: Insert new conjectures
        for c in new_conjectures {
            self.population.insert(c.id, c);
        }

        // Phase 4: Selection pressure — trim to max_population
        let culled = if self.population.len() > self.max_population {
            let mut all: Vec<(ConjectureId, f64)> = self.population.iter()
                .map(|(id, c)| (*id, c.elo))
                .collect();
            // Keep highest Elo (most interesting)
            all.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
            let to_remove: Vec<ConjectureId> = all[self.max_population..]
                .iter()
                .map(|(id, _)| *id)
                .collect();
            let count = to_remove.len();
            for id in to_remove {
                self.population.remove(&id);
            }
            count
        } else {
            0
        };

        let elapsed = start.elapsed();

        EvolutionStats {
            generation: self.generation,
            population_size: self.population.len(),
            mutations_generated,
            culled,
            elapsed_us: elapsed.as_micros() as u64,
            top_elo: self.population.values()
                .map(|c| c.elo)
                .fold(0.0_f64, f64::max),
            bottom_elo: self.population.values()
                .map(|c| c.elo)
                .fold(f64::MAX, f64::min),
        }
    }

    /// Mark a conjecture as proven
    pub fn mark_proven(&mut self, id: &ConjectureId, proof_hash: [u8; 32]) {
        if let Some(c) = self.population.get_mut(id) {
            c.status = VerificationStatus::Proven { proof_hash };
            c.elo += 200.0; // Proven conjectures are high-value
        }
    }

    /// Mark a conjecture as refuted
    pub fn mark_refuted(&mut self, id: &ConjectureId, counterexample: String) {
        if let Some(c) = self.population.get_mut(id) {
            c.status = VerificationStatus::Refuted { counterexample };
            c.elo -= 500.0; // Refuted conjectures lose value
        }
    }

    /// Mark a conjecture as surviving (proof attempt timed out)
    pub fn mark_surviving(&mut self, id: &ConjectureId) {
        if let Some(c) = self.population.get_mut(id) {
            c.status = VerificationStatus::Surviving;
            c.survived_attacks += 1;
            c.elo += 50.0 * c.survived_attacks as f64; // Each survival increases interest
        }
    }

    /// Mark a conjecture as trivial
    pub fn mark_trivial(&mut self, id: &ConjectureId) {
        if let Some(c) = self.population.get_mut(id) {
            c.status = VerificationStatus::Trivial;
            c.elo = 0.0;
        }
    }

    /// Get the top N conjectures by Elo (most interesting)
    pub fn top_conjectures(&self, n: usize) -> Vec<&Conjecture> {
        let mut all: Vec<&Conjecture> = self.population.values().collect();
        all.sort_by(|a, b| b.elo.partial_cmp(&a.elo).unwrap_or(std::cmp::Ordering::Equal));
        all.truncate(n);
        all
    }

    /// Get all surviving (unrefuted, non-trivial) conjectures
    pub fn surviving_conjectures(&self) -> Vec<&Conjecture> {
        self.population.values()
            .filter(|c| matches!(c.status, VerificationStatus::Unverified | VerificationStatus::Surviving))
            .collect()
    }

    /// Get proven conjectures
    pub fn proven_conjectures(&self) -> Vec<&Conjecture> {
        self.population.values()
            .filter(|c| matches!(c.status, VerificationStatus::Proven { .. }))
            .collect()
    }

    /// Population size
    pub fn len(&self) -> usize {
        self.population.len()
    }

    pub fn is_empty(&self) -> bool {
        self.population.is_empty()
    }
}

/// Statistics for one evolution cycle
#[derive(Serialize, Deserialize, Clone, Debug)]
pub struct EvolutionStats {
    pub generation: u32,
    pub population_size: usize,
    pub mutations_generated: usize,
    pub culled: usize,
    pub elapsed_us: u64,
    pub top_elo: f64,
    pub bottom_elo: f64,
}

// ─────────────────────────────────────────────────────────────
// §5 — Tests
// ─────────────────────────────────────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_seed_and_mutate() {
        let mut engine = EvolutionaryConjecturer::new(100);

        engine.seed(
            vec!["∀n ∈ ℕ".into(), "prime(p)".into()],
            "∃q > p : prime(q)".into(),
            800.0,
        );

        engine.add_mutation(MutationOp::Generalize {
            from: "prime".into(),
            to: "odd".into(),
        });
        engine.add_mutation(MutationOp::Negate);
        engine.add_mutation(MutationOp::AddPremise("p > 2".into()));

        let stats = engine.evolve();

        // tracing::info!("═══════════════════════════════════════════");
        // tracing::info!("  EVOLUTIONARY CONJECTURER — Gen {}", stats.generation);
        // tracing::info!("═══════════════════════════════════════════");
        // tracing::info!("  Population:  {}", stats.population_size);
        // tracing::info!("  Mutations:   {}", stats.mutations_generated);
        // tracing::info!("  Culled:      {}", stats.culled);
        // tracing::info!("  Elo range:   [{:.0}, {:.0}]", stats.bottom_elo, stats.top_elo);
        // tracing::info!("  Elapsed:     {} μs", stats.elapsed_us);
        // tracing::info!("═══════════════════════════════════════════");

        assert!(stats.population_size > 1);
        assert!(stats.mutations_generated > 0);
    }

    #[test]
    fn test_crossover() {
        let a = Conjecture {
            id: hash_conjecture(&["p1".into()], "c1"),
            premises: vec!["p1".into()],
            conclusion: "c1".into(),
            elo: 800.0,
            generation: 0,
            origin: ConjectureOrigin::Seed,
            status: VerificationStatus::Unverified,
            survived_attacks: 0,
        };
        let b = Conjecture {
            id: hash_conjecture(&["p2".into()], "c2"),
            premises: vec!["p2".into()],
            conclusion: "c2".into(),
            elo: 600.0,
            generation: 0,
            origin: ConjectureOrigin::Seed,
            status: VerificationStatus::Unverified,
            survived_attacks: 0,
        };

        let children = crossover(&a, &b);
        assert_eq!(children.len(), 2);

        // Type 1: A's premises + B's conclusion
        assert_eq!(children[0].premises, vec!["p1".to_string()]);
        assert_eq!(children[0].conclusion, "c2");

        // Type 2: merged premises + conjunction
        assert!(children[1].premises.contains(&"p1".to_string()));
        assert!(children[1].premises.contains(&"p2".to_string()));
        assert!(children[1].conclusion.contains("∧"));
    }

    #[test]
    fn test_verification_lifecycle() {
        let mut engine = EvolutionaryConjecturer::new(50);

        let id1 = engine.seed(vec!["a".into()], "b".into(), 500.0);
        let id2 = engine.seed(vec!["c".into()], "d".into(), 500.0);
        let id3 = engine.seed(vec!["e".into()], "f".into(), 500.0);

        // Prove one
        engine.mark_proven(&id1, [0u8; 32]);
        assert!(matches!(
            engine.population.get(&id1).unwrap().status,
            VerificationStatus::Proven { .. }
        ));
        assert!(engine.population.get(&id1).unwrap().elo > 500.0);

        // Refute one
        engine.mark_refuted(&id2, "x=42 is counterexample".into());
        assert!(engine.population.get(&id2).unwrap().elo < 500.0);

        // Surviving attack
        engine.mark_surviving(&id3);
        engine.mark_surviving(&id3);
        assert_eq!(engine.population.get(&id3).unwrap().survived_attacks, 2);
        assert!(engine.population.get(&id3).unwrap().elo > 500.0);

        assert_eq!(engine.proven_conjectures().len(), 1);
        assert_eq!(engine.surviving_conjectures().len(), 1);
    }

    #[test]
    fn test_evolution_throughput() {
        let mut engine = EvolutionaryConjecturer::new(500);

        // Seed 10 diverse conjectures
        for i in 0..10 {
            engine.seed(
                vec![format!("hyp_{}_a", i), format!("hyp_{}_b", i)],
                format!("conclusion_{}", i),
                500.0 + i as f64 * 50.0,
            );
        }

        // Add diverse mutations
        engine.add_mutation(MutationOp::Negate);
        engine.add_mutation(MutationOp::AddPremise("extra_hyp".into()));
        engine.add_mutation(MutationOp::Generalize { from: "a".into(), to: "x".into() });
        engine.add_mutation(MutationOp::Swap { a: "a".into(), b: "b".into() });
        engine.add_mutation(MutationOp::Compose("extra_conclusion".into()));

        // Run 5 evolution cycles
        let start = Instant::now();
        let mut total_mutations = 0;
        for _ in 0..5 {
            let stats = engine.evolve();
            total_mutations += stats.mutations_generated;
        }
        let elapsed = start.elapsed();

        // tracing::info!("═══════════════════════════════════════════");
        // tracing::info!("  EVOLUTION THROUGHPUT BENCHMARK");
        // tracing::info!("═══════════════════════════════════════════");
        // tracing::info!("  Seeds:          10");
        // tracing::info!("  Cycles:         5");
        // tracing::info!("  Final pop:      {}", engine.len());
        // tracing::info!("  Total mutants:  {}", total_mutations);
        // tracing::info!("  Elapsed:        {:.4?}", elapsed);
        // tracing::info!("  Rate:           {:.0} conjectures/sec",
            total_mutations as f64 / elapsed.as_secs_f64());
        // tracing::info!("═══════════════════════════════════════════");

        assert!(engine.len() > 10, "Population should grow");
    }

    #[test]
    fn test_population_cap() {
        let mut engine = EvolutionaryConjecturer::new(20);

        for i in 0..15 {
            engine.seed(
                vec![format!("p{}", i)],
                format!("c{}", i),
                100.0 + i as f64 * 100.0,
            );
        }

        engine.add_mutation(MutationOp::Negate);
        engine.add_mutation(MutationOp::AddPremise("extra".into()));

        let stats = engine.evolve();

        assert!(engine.len() <= 20, "Population should be capped at max_population");
        if stats.mutations_generated + 15 > 20 {
            assert!(stats.culled > 0, "Should cull excess population");
        }
    }
}
