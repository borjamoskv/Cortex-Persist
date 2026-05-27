//! CORTEX Genome Mutator — Rust Native AST Manipulation
//! 
//! Exergically efficient calculation of genome mutations to bypass the Python GIL.
//! 
//! Reality Level: C5-REAL

use pyo3::prelude::*;
use rand::Rng;
use serde_json::{Value, json};

#[pyclass]
pub struct GenomeMutatorRs;

#[pymethods]
impl GenomeMutatorRs {
    #[new]
    pub fn new() -> Self {
        GenomeMutatorRs
    }

    /// Mutates the given tree (a JSON string) with a specific mutation type
    /// Returns a new JSON string representing the mutated tree.
    #[staticmethod]
    pub fn mutate_tree(
        tree_json: &str,
        mutation_type: &str,
        generation: u32,
    ) -> PyResult<String> {
        let mut tree: Value = serde_json::from_str(tree_json)
            .map_err(|e| pyo3::exceptions::PyValueError::new_err(format!("Invalid JSON: {}", e)))?;

        let mut rng = rand::thread_rng();

        match mutation_type {
            "parameter_drift" => {
                // Handled in Python or implemented separately since tree is just AgentOp
            }
            "subtree_swap" => {
                let targets = Self::dispatch_targets(&tree);
                if !targets.is_empty() {
                    let old_target = &targets[rng.gen_range(0..targets.len())];
                    let new_target = format!("evolved_{}_{}", old_target, generation);
                    tree = Self::replace_target(tree, old_target, &new_target);
                } else {
                    tree = json!({
                        "Dispatch": {
                            "target": format!("evolved_target_{}", rng.gen_range(100..999)),
                            "parameters": {"source": "subtree_swap"}
                        }
                    });
                }
            }
            "node_insert" => {
                let new_node = json!({
                    "Dispatch": {
                        "target": format!("injected_{}", rng.gen_range(1000..9999)),
                        "parameters": {"gen": generation, "type": "injected"}
                    }
                });
                
                if tree.is_string() || tree == json!("Noop") {
                    tree = new_node;
                } else {
                    if rng.gen_bool(0.5) {
                        tree = json!({"Seq": [tree, new_node]});
                    } else {
                        tree = json!({"Seq": [new_node, tree]});
                    }
                }
            }
            "node_delete" => {
                let targets = Self::dispatch_targets(&tree);
                if !targets.is_empty() {
                    let target_to_remove = &targets[rng.gen_range(0..targets.len())];
                    tree = Self::remove_target(tree, target_to_remove);
                }
            }
            "parallelize" => {
                if let Some(obj) = tree.as_object() {
                    if let Some(seq_arr) = obj.get("Seq") {
                        tree = json!({"Par": seq_arr});
                    }
                }
            }
            "sequentialize" => {
                if let Some(obj) = tree.as_object() {
                    if let Some(par_arr) = obj.get("Par") {
                        tree = json!({"Seq": par_arr});
                    }
                }
            }
            "loop_unroll" => {
                if let Some(obj) = tree.as_object() {
                    if let Some(loop_obj) = obj.get("Loop") {
                        let count = loop_obj.get("count").and_then(|c| c.as_u64()).unwrap_or(1);
                        let fallback = json!("Noop");
                        let body = loop_obj.get("body").unwrap_or(&fallback);
                        if count <= 5 {
                            let mut seq_arr = Vec::new();
                            for _ in 0..count {
                                seq_arr.push(body.clone());
                            }
                            tree = json!({"Seq": seq_arr});
                        }
                    }
                }
            }
            "conditional_inject" => {
                tree = json!({
                    "Cond": {
                        "predicate": {"type": "always"},
                        "then_branch": tree,
                        "else_branch": {
                            "Halt": {"error": "conditional_guard_failed"}
                        }
                    }
                });
            }
            "strategy_synthesis" => {
                let mut strategies = vec![
                    json!({
                        "Par": [
                            {"Dispatch": {"target": "synth_alpha", "parameters": {"mode": "scan"}, "id": rng.gen_range(100..999)}},
                            {"Dispatch": {"target": "synth_beta", "parameters": {"mode": "extract"}, "id": rng.gen_range(100..999)}},
                            {"Dispatch": {"target": "synth_gamma", "parameters": {"mode": "verify"}, "id": rng.gen_range(100..999)}}
                        ]
                    }),
                    json!({
                        "Seq": [
                            {"Dispatch": {"target": "synth_ingest", "parameters": {"phase": 1}}},
                            {"Dispatch": {"target": "synth_process", "parameters": {"phase": 2}}},
                            {"Dispatch": {"target": "synth_emit", "parameters": {"phase": 3}}}
                        ]
                    }),
                    json!({
                        "Cond": {
                            "predicate": {"type": "always"},
                            "then_branch": {
                                "Seq": [
                                    {"Dispatch": {"target": "synth_primary", "parameters": {}}},
                                    {"Dispatch": {"target": "synth_validate", "parameters": {}}}
                                ]
                            },
                            "else_branch": {"Dispatch": {"target": "synth_fallback", "parameters": {}}}
                        }
                    }),
                    json!({
                        "Seq": [
                            {"Dispatch": {"target": "synth_init", "parameters": {}}},
                            {"Loop": {"count": 3, "body": {"Dispatch": {"target": "synth_iterate", "parameters": {"cycle": true}}}}},
                            {"Dispatch": {"target": "synth_finalize", "parameters": {}}}
                        ]
                    })
                ];
                tree = strategies.swap_remove(rng.gen_range(0..strategies.len()));
            }
            _ => {}
        }

        Ok(serde_json::to_string(&tree).unwrap())
    }
}

impl GenomeMutatorRs {
    fn dispatch_targets(tree: &Value) -> Vec<String> {
        let mut targets = Vec::new();
        match tree {
            Value::Object(map) => {
                if let Some(dispatch) = map.get("Dispatch") {
                    if let Some(target) = dispatch.get("target").and_then(|t| t.as_str()) {
                        targets.push(target.to_string());
                    }
                } else if let Some(seq) = map.get("Seq") {
                    targets.extend(Self::dispatch_targets(seq));
                } else if let Some(par) = map.get("Par") {
                    targets.extend(Self::dispatch_targets(par));
                } else if let Some(cond) = map.get("Cond") {
                    if let Some(then_b) = cond.get("then_branch") {
                        targets.extend(Self::dispatch_targets(then_b));
                    }
                    if let Some(else_b) = cond.get("else_branch") {
                        targets.extend(Self::dispatch_targets(else_b));
                    }
                } else if let Some(loop_n) = map.get("Loop") {
                    if let Some(body) = loop_n.get("body") {
                        targets.extend(Self::dispatch_targets(body));
                    }
                }
            }
            Value::Array(arr) => {
                for item in arr {
                    targets.extend(Self::dispatch_targets(item));
                }
            }
            _ => {}
        }
        targets
    }

    fn replace_target(tree: Value, old_target: &str, new_target: &str) -> Value {
        match tree {
            Value::Object(mut map) => {
                if let Some(dispatch) = map.get_mut("Dispatch") {
                    if let Some(target) = dispatch.get("target").and_then(|t| t.as_str()) {
                        if target == old_target {
                            if let Some(obj) = dispatch.as_object_mut() {
                                obj.insert("target".to_string(), Value::String(new_target.to_string()));
                            }
                        }
                    }
                } else if let Some(seq) = map.get_mut("Seq") {
                    *seq = Self::replace_target(seq.clone(), old_target, new_target);
                } else if let Some(par) = map.get_mut("Par") {
                    *par = Self::replace_target(par.clone(), old_target, new_target);
                } else if let Some(cond) = map.get_mut("Cond") {
                    if let Some(then_b) = cond.get_mut("then_branch") {
                        *then_b = Self::replace_target(then_b.clone(), old_target, new_target);
                    }
                    if let Some(else_b) = cond.get_mut("else_branch") {
                        *else_b = Self::replace_target(else_b.clone(), old_target, new_target);
                    }
                } else if let Some(loop_n) = map.get_mut("Loop") {
                    if let Some(body) = loop_n.get_mut("body") {
                        *body = Self::replace_target(body.clone(), old_target, new_target);
                    }
                }
                Value::Object(map)
            }
            Value::Array(arr) => {
                let new_arr = arr.into_iter().map(|item| Self::replace_target(item, old_target, new_target)).collect();
                Value::Array(new_arr)
            }
            other => other
        }
    }

    fn remove_target(tree: Value, target_to_remove: &str) -> Value {
        match tree {
            Value::Object(mut map) => {
                if let Some(dispatch) = map.get("Dispatch") {
                    if let Some(target) = dispatch.get("target").and_then(|t| t.as_str()) {
                        if target == target_to_remove {
                            return Value::String("Noop".to_string());
                        }
                    }
                } else if let Some(seq) = map.get_mut("Seq") {
                    let mut new_arr = Vec::new();
                    if let Some(arr) = seq.as_array() {
                        for item in arr {
                            let updated = Self::remove_target(item.clone(), target_to_remove);
                            if updated != Value::String("Noop".to_string()) {
                                new_arr.push(updated);
                            }
                        }
                    }
                    if new_arr.is_empty() {
                        return Value::String("Noop".to_string());
                    }
                    *seq = Value::Array(new_arr);
                } else if let Some(par) = map.get_mut("Par") {
                    let mut new_arr = Vec::new();
                    if let Some(arr) = par.as_array() {
                        for item in arr {
                            let updated = Self::remove_target(item.clone(), target_to_remove);
                            if updated != Value::String("Noop".to_string()) {
                                new_arr.push(updated);
                            }
                        }
                    }
                    if new_arr.is_empty() {
                        return Value::String("Noop".to_string());
                    }
                    *par = Value::Array(new_arr);
                } else if let Some(cond) = map.get_mut("Cond") {
                    if let Some(then_b) = cond.get_mut("then_branch") {
                        *then_b = Self::remove_target(then_b.clone(), target_to_remove);
                    }
                    if let Some(else_b) = cond.get_mut("else_branch") {
                        *else_b = Self::remove_target(else_b.clone(), target_to_remove);
                    }
                } else if let Some(loop_n) = map.get_mut("Loop") {
                    if let Some(body) = loop_n.get_mut("body") {
                        *body = Self::remove_target(body.clone(), target_to_remove);
                    }
                }
                Value::Object(map)
            }
            other => other
        }
    }
}
