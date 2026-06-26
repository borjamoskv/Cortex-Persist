// [C5-REAL] Exergy-Maximized
// Decay Functions for Spaced Repetition
// Anchored at: cortex/engine/causal/decay_functions.rs

/// Reality Level: #C5-REAL
/// Calculates the retrieval strength based on time elapsed and memory stability.
/// Uses a negative exponential decay function: R = e^(-t / S)
pub fn calculate_retrieval_strength(time_elapsed_days: f64, stability: f64) -> f64 {
    (-time_elapsed_days / stability).exp()
}

/// Computes the exact time in days when retrieval strength drops below 85%
pub fn time_to_reactivation(stability: f64) -> f64 {
    let target_retrieval = 0.85;
    -stability * target_retrieval.ln()
}

/// Updates the memory stability after a review session.
/// Implementation inspired by SuperMemo-2.
pub fn update_stability(previous_stability: f64, quality_of_recall: u8) -> f64 {
    // Quality: 0-5 scale. 5 = perfect recall, 0 = complete blackout
    let q = quality_of_recall.clamp(0, 5) as f64;
    
    // Growth factor depends on the quality of recall
    let growth_factor = if q >= 3.0 {
        1.0 + (q - 3.0) * 0.5
    } else {
        // If quality is low, stability degrades or resets
        0.5
    };
    
    previous_stability * growth_factor
}

/// Struct representing the Biological RAM state of an EDG node for a student
#[derive(Debug, Clone)]
pub struct MemoryNode {
    pub stability: f64,
    pub last_review_timestamp: u64,
}

impl MemoryNode {
    pub fn new() -> Self {
        Self {
            stability: 1.0, // Initial stability of 1 day
            last_review_timestamp: 0,
        }
    }

    /// Triggers a review, calculating if the node requires reactivation
    pub fn review(&mut self, quality: u8, current_timestamp: u64) -> bool {
        let time_elapsed_days = (current_timestamp - self.last_review_timestamp) as f64 / 86400.0;
        let requires_reactivation = calculate_retrieval_strength(time_elapsed_days, self.stability) < 0.85;
        
        self.stability = update_stability(self.stability, quality);
        self.last_review_timestamp = current_timestamp;
        
        requires_reactivation
    }
}
