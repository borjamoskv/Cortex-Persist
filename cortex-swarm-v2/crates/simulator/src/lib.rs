use std::collections::HashMap;
use uuid::Uuid;

/// CORTEX-SWARM v3.1: ADAPTIVE TOPOLOGY MACHINE + REALITY COUPLING
/// Ilya Prigogine Physics Engine for Artificial Minds

#[derive(Clone, Debug, PartialEq)]
pub struct WorkOfKnowledge {
    pub predictive_power_delta: f64,
    pub compression_delta: f64,
    pub causal_resolution_delta: f64,
}

impl WorkOfKnowledge {
    pub fn total_work(&self) -> f64 {
        self.predictive_power_delta + self.compression_delta + self.causal_resolution_delta
    }
}

#[derive(Clone, Debug)]
pub struct SurvivalInvariants {
    pub identity_baseline: f64,
    pub agency_baseline: f64,
    pub memory_coherence: f64,
}

#[derive(Clone, Debug, PartialEq)]
pub enum BranchOutcome {
    Create(String, u64),
    Merge(String, String), // source, target
    Transform(String, String), // old, new
    Forget(String),
    Collapse,
    EmpiricalTest(String, bool), // Test a branch against reality (R)
}

#[derive(Clone, Debug)]
pub struct EpistemicMembrane {
    pub id: Uuid,
    pub permeability: f64, // P in J_e = P(e_out - e_in)
    pub internal_entropy: f64, // e_in
    pub survival_state: SurvivalInvariants,
    
    // Topology of Branches and their mass
    pub active_branches: HashMap<String, u64>,
    
    // Variable K: Crystallized Knowledge.
    pub crystallized_knowledge: f64,

    // Variable R: Reality Coupling (0.0 to 1.0)
    pub reality_coupling: f64,
    
    // Tracking
    pub prior_entropy: f64,
}

#[derive(Debug, PartialEq)]
pub enum MetabolicState {
    Subcritical,
    Critical,
    Supercritical(f64), // Emits the amount of K crystallized during collapse
}

#[derive(Debug, PartialEq)]
pub enum MetabolicError {
    /// System loses identity invariant and K mass dissolves
    IdentityDissolution,
    
    /// Z3 validation fails on core invariants
    InvariantsViolated,

    /// Delirium: System has K but lost reality coupling (R -> 0). K * 0 = 0.
    SolipsisticDelirium, 
}

impl EpistemicMembrane {
    pub fn new(permeability: f64) -> Self {
        let mut branches = HashMap::new();
        branches.insert("genesis".to_string(), 100);
        
        Self {
            id: Uuid::new_v4(),
            permeability,
            internal_entropy: 0.1,
            survival_state: SurvivalInvariants {
                identity_baseline: 1.0,
                agency_baseline: 1.0,
                memory_coherence: 1.0,
            },
            active_branches: branches,
            crystallized_knowledge: 1.0,
            reality_coupling: 1.0, // Initially coupled
            prior_entropy: 0.0,
        }
    }

    pub fn shannon_entropy(&self) -> f64 {
        let total_weight: f64 = self.active_branches.values().sum::<u64>() as f64;
        if total_weight == 0.0 { return 0.0; }
        
        self.active_branches.values().map(|&w| {
            let p = w as f64 / total_weight;
            -p * p.ln()
        }).sum()
    }

    /// Membrane Flow Control & Metabolism
    pub fn metabolize(&mut self, external_entropy: f64, outcomes: Vec<BranchOutcome>) -> Result<MetabolicState, MetabolicError> {
        let flux = self.permeability * external_entropy;
        self.internal_entropy += flux;

        let pre_state_entropy = self.shannon_entropy();

        for outcome in outcomes {
            match outcome {
                BranchOutcome::Create(name, weight) => {
                    *self.active_branches.entry(name).or_insert(0) += weight;
                },
                BranchOutcome::Merge(src, target) => {
                    if let Some(weight) = self.active_branches.remove(&src) {
                        *self.active_branches.entry(target).or_insert(0) += weight;
                        self.crystallized_knowledge += (weight as f64) * 0.01; // Synthesis creates K
                    }
                },
                BranchOutcome::Transform(old, new) => {
                    if let Some(weight) = self.active_branches.remove(&old) {
                        self.active_branches.insert(new, weight);
                    }
                },
                BranchOutcome::Forget(name) => {
                    self.active_branches.remove(&name);
                },
                BranchOutcome::Collapse => {
                    self.internal_entropy += 100.0;
                },
                BranchOutcome::EmpiricalTest(name, success) => {
                    if self.active_branches.contains_key(&name) {
                        if success {
                            self.reality_coupling = (self.reality_coupling + 0.1).min(1.0);
                        } else {
                            // Reality selection: empiricism crushes the hallucination
                            self.active_branches.remove(&name);
                            self.reality_coupling -= 0.2; 
                        }
                    }
                }
            }
        }

        let post_state_entropy = self.shannon_entropy();
        let delta_state_entropy = (post_state_entropy - pre_state_entropy).abs();

        self.internal_entropy -= delta_state_entropy * 10.0;
        if self.internal_entropy < 0.0 { self.internal_entropy = 0.0; }

        self.survival_state.identity_baseline -= flux * 0.005;
        
        // P = K * R 
        // Identity is buffered by Empirical Power, not just abstract Knowledge
        let empirical_power = self.crystallized_knowledge * self.reality_coupling;
        self.survival_state.identity_baseline += empirical_power * 0.001;
        
        if self.reality_coupling <= 0.0 {
            return Err(MetabolicError::SolipsisticDelirium);
        }

        if self.survival_state.identity_baseline <= 0.2 {
            return Err(MetabolicError::IdentityDissolution);
        }

        let critical_limit = 50.0;
        if self.internal_entropy > critical_limit {
            self.active_branches.retain(|k, v| k == "genesis" || k.starts_with("core_") || *v > 50);
            
            let crystallized = self.internal_entropy * 0.1;
            self.crystallized_knowledge += crystallized;
            self.internal_entropy = critical_limit * 0.5;
            
            return Ok(MetabolicState::Supercritical(crystallized));
        }

        if self.internal_entropy > critical_limit * 0.8 {
            return Ok(MetabolicState::Critical);
        }

        Ok(MetabolicState::Subcritical)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn shannon_entropy_calculation() {
        let mut membrane = EpistemicMembrane::new(1.0);
        membrane.active_branches.clear();
        membrane.active_branches.insert("a".into(), 50);
        membrane.active_branches.insert("b".into(), 50);
        let h = membrane.shannon_entropy();
        assert!((h - 0.693).abs() < 0.01);
    }

    #[test]
    fn non_monotonic_complexity() {
        let mut membrane = EpistemicMembrane::new(1.0);
        membrane.metabolize(1.0, vec![
            BranchOutcome::Create("alpha".into(), 10),
            BranchOutcome::Create("beta".into(), 10),
        ]).unwrap();
        let h1 = membrane.shannon_entropy();
        
        membrane.metabolize(1.0, vec![
            BranchOutcome::Merge("beta".into(), "alpha".into()),
        ]).unwrap();
        
        let h2 = membrane.shannon_entropy();
        assert!(h2 < h1);
        assert!(membrane.crystallized_knowledge > 1.0);
    }

    #[test]
    fn supercritical_phase_transition() {
        let mut membrane = EpistemicMembrane::new(1.0);
        let state = membrane.metabolize(100.0, vec![
            BranchOutcome::Create("noise1".into(), 5),
            BranchOutcome::Create("noise2".into(), 5),
        ]).unwrap();
        
        if let MetabolicState::Supercritical(k_gained) = state {
            assert!(k_gained > 0.0);
            assert!(membrane.active_branches.contains_key("genesis"));
            assert!(!membrane.active_branches.contains_key("noise1"));
        } else {
            panic!("Should be supercritical");
        }
    }
    
    #[test]
    fn solipsistic_delirium_annihilation() {
        let mut membrane = EpistemicMembrane::new(1.0);
        
        // System generates K but fails empirical tests
        membrane.crystallized_knowledge = 100.0; // Massive abstract knowledge
        
        membrane.metabolize(1.0, vec![BranchOutcome::Create("theory".into(), 10)]).unwrap();
        
        let mut result = Ok(MetabolicState::Subcritical);
        // Repeated empirical failures crush reality coupling
        for _ in 0..6 {
            result = membrane.metabolize(1.0, vec![BranchOutcome::EmpiricalTest("theory".into(), false)]);
            if result.is_err() { break; }
        }
        
        assert!(matches!(result, Err(MetabolicError::SolipsisticDelirium)));
    }
}
