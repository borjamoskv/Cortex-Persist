//! OUROBOROS COMPILER v0.1
//! Limerent Agent Compiler for CORTEX-Persist
//! Self-modifying agent swarm compiler (C5-REAL live system)

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Definición formal de un agente en el entorno de fricción
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentNode {
    pub id: String,
    pub goal: String,
    pub energy: f64,
    pub friction: f64,
    pub limerence: f64,
    pub repetition: f64,
    pub stability: f64,
    pub maintenance_cost: f64,
    pub self_rewrite_rate: f64,
    pub memory: Vec<String>,
}

/// OUROBOROS EXECUTION GRAPH (OEG)
#[derive(Debug)]
pub struct OuroborosExecutionGraph {
    pub nodes: HashMap<String, AgentNode>,
    pub edges: Vec<(String, String, f64)>, // (Source, Target, Friction Weight)
}

impl OuroborosExecutionGraph {
    pub fn new() -> Self {
        Self {
            nodes: HashMap::new(),
            edges: Vec::new(),
        }
    }

    /// PHASE 1 — PARSE (Semantic Digestion)
    pub fn parse_swarm(&mut self, agents_input: Vec<AgentNode>) {
        for mut a in agents_input {
            a.energy = self.estimate_exergy(&a.goal);
            a.friction = self.detect_conflict(&a.memory);
            self.nodes.insert(a.id.clone(), a);
        }
    }

    fn estimate_exergy(&self, _goal: &str) -> f64 {
        // En C5-REAL esto extrae entropía de la fricción estructural
        1.0 
    }

    fn detect_conflict(&self, _memory: &[String]) -> f64 {
        // Medición de densidad de enlaces contradictorios
        0.8 
    }

    /// PHASE 2 — LIMERENCE VECTORIZATION
    pub fn vectorize_limerence(&mut self, alpha: f64, beta: f64, gamma: f64) {
        for node in self.nodes.values_mut() {
            // L = α*R + β*F - γ*S
            node.limerence = (alpha * node.repetition) + (beta * node.friction) - (gamma * node.stability);
        }
    }

    /// PHASE 3 — OUROBOROS LINKING
    pub fn link_ouroboros_cycles(&mut self) {
        // Todo nodo debe poder destruirse a sí mismo indirectamente
        let ids: Vec<String> = self.nodes.keys().cloned().collect();
        for i in 0..ids.len() {
            let src = &ids[i];
            let tgt = &ids[(i + 1) % ids.len()];
            let weight = self.nodes[src].limerence + self.nodes[tgt].limerence;
            self.edges.push((src.clone(), tgt.clone(), weight));
        }
    }

    /// PHASE 4 — EXERGY FILTER
    pub fn filter_exergy(&mut self) {
        self.nodes.retain(|_, n| n.energy > n.maintenance_cost);
    }

    /// PHASE 5 — FRACTAL REWRITE ENGINE
    pub fn fractal_rewrite(&mut self) {
        for node in self.nodes.values_mut() {
            if node.friction > 0.8 {
                // A1 -> A1' (menos memoria, más señal)
                node.memory.truncate(node.memory.len() / 2);
                node.energy += 0.5; // Incrementa señal tras compresión
                node.self_rewrite_rate += 1.0;
            }
        }
    }

    /// PHASE 6 — RUNTIME EXECUTION LOOP (C5-REAL Tick)
    pub fn execution_tick(&mut self) {
        // 1. Execute graph (simulated traversal)
        // 2. Measure friction
        self.vectorize_limerence(1.0, 1.5, 0.5);
        // 3. Prune low signal nodes
        self.filter_exergy();
        // 4. Rewrite high friction nodes
        self.fractal_rewrite();
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_c5_real_apoptosis_and_rewrite() {
        let mut graph = OuroborosExecutionGraph::new();
        
        let mut agents = vec![];
        for i in 0..10 {
            agents.push(AgentNode {
                id: format!("A{}", i),
                goal: "maximizar señal".to_string(),
                energy: 0.0,
                friction: 0.0,
                limerence: 0.0,
                repetition: if i % 2 == 0 { 5.0 } else { 0.1 }, // Even agents loop more
                stability: if i % 3 == 0 { 10.0 } else { 1.0 }, // Every 3rd is too stable
                maintenance_cost: 0.5,
                self_rewrite_rate: 0.0,
                memory: vec!["mem1".to_string(), "mem2".to_string(), "mem3".to_string()],
            });
        }

        graph.parse_swarm(agents);
        
        // Simular inyección termodinámica de fricción empírica
        for node in graph.nodes.values_mut() {
            node.friction = if node.repetition > 2.0 { 0.9 } else { 0.1 };
            node.energy = if node.stability > 5.0 { 0.1 } else { 2.0 }; // Stable ones lack energy
        }

        graph.link_ouroboros_cycles();
        
        // The tick processes limerence vectorization, exergy filtering and fractal rewrite
        graph.execution_tick();

        // 1. Apoptosis (Exergy Filter)
        // Stable nodes had energy=0.1 < maintenance=0.5, so they must be purged
        assert!(!graph.nodes.contains_key("A0")); // stable
        assert!(!graph.nodes.contains_key("A3")); // stable
        assert!(!graph.nodes.contains_key("A6")); // stable
        assert!(!graph.nodes.contains_key("A9")); // stable

        // 2. Fractal Rewrite Engine
        // Node A2 is not stable (energy 2.0 > 0.5), has high friction (0.9 > 0.8)
        let a2 = graph.nodes.get("A2").unwrap();
        // Memory should be truncated to len / 2 (3/2 = 1)
        assert_eq!(a2.memory.len(), 1);
        // Energy should increase +0.5
        assert_eq!(a2.energy, 2.5);
        // Rewrite rate should increment
        assert_eq!(a2.self_rewrite_rate, 1.0);
    }
}
