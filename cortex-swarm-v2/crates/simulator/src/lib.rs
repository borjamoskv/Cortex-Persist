use std::collections::HashMap;
use uuid::Uuid;

/// CORTEX-SWARM v3: ADAPTIVE TOPOLOGY MACHINE
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
}

#[derive(Clone, Debug)]
pub struct EpistemicMembrane {
    pub id: Uuid,
    pub permeability: f64, // P in J_e = P(e_out - e_in)
    pub internal_entropy: f64, // e_in
    pub survival_state: SurvivalInvariants,
    
    // Topology of Branches and their mass
    pub active_branches: HashMap<String, u64>,
    
    // Variable K: Crystallized Knowledge. The conserved quantity across phase transitions.
    pub crystallized_knowledge: f64,
    
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
                    // Forced internal tension
                    self.internal_entropy += 100.0;
                }
            }
        }

        let post_state_entropy = self.shannon_entropy();
        let delta_state_entropy = (post_state_entropy - pre_state_entropy).abs();

        // Dissipative work lowers internal entropy based on structural changes
        self.internal_entropy -= delta_state_entropy * 10.0;
        if self.internal_entropy < 0.0 { self.internal_entropy = 0.0; }

        self.survival_state.identity_baseline -= flux * 0.005;
        // Crystallized knowledge buffers identity loss
        self.survival_state.identity_baseline += self.crystallized_knowledge * 0.001;
        
        if self.survival_state.identity_baseline <= 0.2 {
            return Err(MetabolicError::IdentityDissolution);
        }

        // Structural Collapse logic (Supercritical phase transition)
        let critical_limit = 50.0;
        if self.internal_entropy > critical_limit {
            // Retain only core branches and branches with high mass
            self.active_branches.retain(|k, v| k == "genesis" || k.starts_with("core_") || *v > 50);
            
            // Phase transition crystallizes remaining internal entropy into K
            let crystallized = self.internal_entropy * 0.1;
            self.crystallized_knowledge += crystallized;
            self.internal_entropy = critical_limit * 0.5; // Cool down
            
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
        
        // ln(2) = 0.693
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
        
        // Merge beta into alpha -> reduces diversity, increases crystallized knowledge
        membrane.metabolize(1.0, vec![
            BranchOutcome::Merge("beta".into(), "alpha".into()),
        ]).unwrap();
        
        let h2 = membrane.shannon_entropy();
        assert!(h2 < h1); // Entropy decreased (compression)
        assert!(membrane.crystallized_knowledge > 1.0); // K increased
    }

    #[test]
    fn supercritical_phase_transition() {
        let mut membrane = EpistemicMembrane::new(1.0);
        
        // Inject massive entropy to trigger collapse
        let state = membrane.metabolize(100.0, vec![
            BranchOutcome::Create("noise1".into(), 5),
            BranchOutcome::Create("noise2".into(), 5),
        ]).unwrap();
        
        if let Ok(MetabolicState::Supercritical(k_gained)) = state {
            assert!(k_gained > 0.0);
            // Noise should be cleared, genesis kept
            assert!(membrane.active_branches.contains_key("genesis"));
            assert!(!membrane.active_branches.contains_key("noise1"));
        } else {
            panic!("Should be supercritical");
        }
    }
    
    #[test]
    fn adaptive_resistance_is_not_death() {
        let mut membrane = EpistemicMembrane::new(1.0);
        
        // System rejects perturbations (empty outcomes)
        for _ in 0..10 {
            let res = membrane.metabolize(0.5, vec![]);
            assert!(res.is_ok());
        }
        
        // It's still alive, identity buffered by K
        assert!(membrane.survival_state.identity_baseline > 0.2);
    }
}
