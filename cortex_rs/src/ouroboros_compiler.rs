//! OUROBOROS COMPILER v0.1
//! Limerent Agent Compiler for CORTEX-Persist
//! Self-modifying agent swarm compiler (C5-REAL live system)

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use pyo3::prelude::*;
use pyo3::exceptions::PyValueError;

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
#[pyclass]
#[derive(Debug)]
pub struct OuroborosExecutionGraph {
    pub nodes: HashMap<String, AgentNode>,
    pub edges: Vec<(String, String, f64)>, // (Source, Target, Friction Weight)
}

#[pymethods]
impl OuroborosExecutionGraph {
    #[new]
    pub fn new() -> Self {
        Self {
            nodes: HashMap::new(),
            edges: Vec::new(),
        }
    }

    /// PHASE 1 — PARSE (Semantic Digestion) from JSON
    pub fn parse_swarm(&mut self, agents_json: &str) -> PyResult<()> {
        let agents_input: Vec<AgentNode> = serde_json::from_str(agents_json)
            .map_err(|e| PyValueError::new_err(format!("Failed to parse agents: {}", e)))?;
            
        for mut a in agents_input {
            a.energy = self.estimate_exergy(&a.goal);
            a.friction = self.detect_conflict(&a.memory);
            self.nodes.insert(a.id.clone(), a);
        }
        Ok(())
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
        let ids: Vec<String> = self.nodes.keys().cloned().collect();
        if ids.is_empty() { return; }
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
    pub fn fractal_rewrite(&mut self, ring_buffer: Option<&crate::ZeroCopyRingBuffer>) {
        for node in self.nodes.values_mut() {
            if node.friction > 0.8 {
                // A1 -> A1' (menos memoria, más señal)
                node.memory.truncate(node.memory.len() / 2);
                node.energy += 0.5; // Incrementa señal tras compresión
                node.self_rewrite_rate += 1.0;
                
                // C5-REAL: Emit zero-copy rewrite command to the ring buffer
                if let Some(rb) = ring_buffer {
                    let payload = format!(r#"{{"op":"AST_REWRITE","target":"{}"}}"#, node.id);
                    let _ = rb.enqueue(node.id.as_bytes(), payload.as_bytes());
                }
            }
        }
    }

    /// PHASE 6 — RUNTIME EXECUTION LOOP (C5-REAL Tick)
    #[pyo3(signature = (ring_buffer=None))]
    pub fn execution_tick(&mut self, ring_buffer: Option<PyRef<'_, crate::ZeroCopyRingBuffer>>) {
        self.vectorize_limerence(1.0, 1.5, 0.5);
        self.filter_exergy();
        let rb_ref = ring_buffer.as_deref();
        self.fractal_rewrite(rb_ref);
    }
    
    /// Extract Graph state as JSON
    pub fn state_json(&self) -> PyResult<String> {
        let state = serde_json::json!({
            "nodes": self.nodes,
            "edges": self.edges
        });
        serde_json::to_string(&state)
            .map_err(|e| PyValueError::new_err(format!("Serialize error: {}", e)))
    }
}

impl OuroborosExecutionGraph {
    fn estimate_exergy(&self, _goal: &str) -> f64 {
        1.0 
    }

    fn detect_conflict(&self, _memory: &[String]) -> f64 {
        0.8 
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

        let agents_json = serde_json::to_string(&agents).unwrap();
        graph.parse_swarm(&agents_json).unwrap();
        
        // Simular inyección termodinámica de fricción empírica
        for node in graph.nodes.values_mut() {
            node.friction = if node.repetition > 2.0 { 0.9 } else { 0.1 };
            node.energy = if node.stability > 5.0 { 0.1 } else { 2.0 }; // Stable ones lack energy
        }

        graph.link_ouroboros_cycles();
        
        // The tick processes limerence vectorization, exergy filtering and fractal rewrite
        graph.execution_tick(None);

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
