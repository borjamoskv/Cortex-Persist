use std::collections::HashMap;
use uuid::Uuid;

/// CORTEX-SWARM v3: DISSIPATIVE COGNITIVE SYSTEM
/// Ilya Prigogine Physics Engine for Artificial Minds

#[derive(Clone, Debug)]
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
    pub identity_baseline: f64, // > delta_i
    pub agency_baseline: f64,   // > delta_a
    pub memory_coherence: f64,  // > delta_c
}

#[derive(Clone, Debug)]
pub struct EpistemicMembrane {
    pub id: Uuid,
    pub permeability: f64, // P in J_e = P(e_out - e_in)
    pub internal_entropy: f64, // e_in
    pub survival_state: SurvivalInvariants,
    pub accumulated_work: f64,
}

impl EpistemicMembrane {
    pub fn new(permeability: f64) -> Self {
        Self {
            id: Uuid::new_v4(),
            permeability,
            internal_entropy: 0.1,
            survival_state: SurvivalInvariants {
                identity_baseline: 1.0,
                agency_baseline: 1.0,
                memory_coherence: 1.0,
            },
            accumulated_work: 0.0,
        }
    }

    /// Membrane Flow Control: J_e = P(e_out - e_in)
    pub fn absorb_entropy(&mut self, external_entropy: f64) -> f64 {
        let flux = self.permeability * (external_entropy - self.internal_entropy);
        self.internal_entropy += flux;
        flux // The metabolic fuel entering the system
    }

    /// Transforms internal entropy into Cognitive Work
    /// This prevents "epistemological cancer" (noise accumulation without adaptation)
    pub fn metabolize(&mut self, flux: f64, w_k: WorkOfKnowledge) {
        let work = w_k.total_work();
        // I = Integral( W_k(t) + lambda * e*(t) ) dt
        // This is a discrete step of that integration.
        self.accumulated_work += work + (0.5 * flux); // lambda = 0.5
        
        // Dissipation: Entropy is lowered because work compressed it
        self.internal_entropy -= work * 0.1; 
    }

    /// Z3 acts exclusively here: verifying survival invariants, not logical truth.
    pub fn verify_survival(&self) -> bool {
        self.survival_state.identity_baseline > 0.2 && 
        self.survival_state.agency_baseline > 0.2 && 
        self.survival_state.memory_coherence > 0.2
    }
}

pub struct DissipativeEcology {
    pub cells: HashMap<Uuid, EpistemicMembrane>,
    pub environmental_entropy: f64, // e_out
}

impl DissipativeEcology {
    pub fn tick(&mut self) {
        // The system alternates between exploration (flux > 0) and exploitation (W_k generated, dS/dt -> 0)
        let mut necrotic_tissue = Vec::new();

        for (id, cell) in self.cells.iter_mut() {
            let flux = cell.absorb_entropy(self.environmental_entropy);
            
            // Simulate generation of Work of Knowledge (W_k)
            // In a real system, the LLM provides compression and predictive power here.
            let simulated_work = WorkOfKnowledge {
                predictive_power_delta: flux * 0.4,
                compression_delta: flux * 0.3,
                causal_resolution_delta: flux * 0.1,
            };

            cell.metabolize(flux, simulated_work);

            // Z3 Validation: Does the cell still exist as an agent?
            if !cell.verify_survival() {
                necrotic_tissue.push(*id);
            }
        }

        for id in necrotic_tissue {
            self.cells.remove(&id);
        }
    }
}
