// [C5-REAL] Exergy-Maximized
// Adaptive Curriculum Finite State Machine
// Anchored at: cortex/engine/adaptive_curriculum.rs

use std::collections::{HashMap, HashSet};

/// Reality Level: #C5-REAL
/// EDG (Epistemic Dependency Graph) Node representing a discrete concept.
#[derive(Debug, Clone, Eq, PartialEq, Hash)]
pub struct EDGNode {
    pub id: String,
    pub complexity: u32,
    pub dependencies: Vec<String>,
}

#[derive(Debug, Clone)]
pub struct StudentEmpiricalData {
    pub latency_ms: u64,
    pub error_rate: f64,
    pub node_id: String,
}

pub struct AdaptiveCurriculum {
    pub nodes: HashMap<String, EDGNode>,
    pub mastery: HashMap<String, f64>,
}

impl AdaptiveCurriculum {
    pub fn new() -> Self {
        Self {
            nodes: HashMap::new(),
            mastery: HashMap::new(),
        }
    }

    pub fn add_node(&mut self, node: EDGNode) {
        self.nodes.insert(node.id.clone(), node);
    }

    /// Evaluates empirical validation to mutate the mastery topology.
    pub fn evaluate_empirical_validation(&mut self, data: &StudentEmpiricalData) -> bool {
        // Deterministic mutation of the knowledge topology
        // Target: Zero Anergy. No heuristic LLM inference.
        
        let mut mastery_delta = 0.0;
        
        // Exergy cost inversion: high latency on low complexity reduces mastery.
        let expected_latency = match self.nodes.get(&data.node_id) {
            Some(node) => node.complexity as u64 * 1000,
            None => return false,
        };

        if data.error_rate > 0.5 {
            mastery_delta -= 0.2;
        } else if data.error_rate == 0.0 {
            if data.latency_ms <= expected_latency {
                mastery_delta += 0.2;
            } else {
                mastery_delta += 0.1;
            }
        } else {
            mastery_delta -= 0.1;
        }

        let current_mastery = self.mastery.entry(data.node_id.clone()).or_insert(0.0);
        *current_mastery = (*current_mastery + mastery_delta).clamp(0.0, 1.0);

        true
    }

    /// Calculates the optimal vector of exposure to new material
    pub fn recalculate_optimal_vector(&self) -> Vec<String> {
        let mut optimal_vector = Vec::new();
        
        for (node_id, node) in &self.nodes {
            let mastery = self.mastery.get(node_id).unwrap_or(&0.0);
            if *mastery < 0.8 {
                // Check if dependencies are met
                let deps_met = node.dependencies.iter().all(|dep| {
                    *self.mastery.get(dep).unwrap_or(&0.0) >= 0.8
                });
                
                if deps_met {
                    optimal_vector.push(node_id.clone());
                }
            }
        }
        
        // Sort by complexity ascending
        optimal_vector.sort_by_key(|id| self.nodes.get(id).unwrap().complexity);
        optimal_vector
    }
}
