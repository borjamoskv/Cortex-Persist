//! CORTEX-TAINT Engine — SHA-256 deterministic hashing for sovereign ledger.
//!
//! AX-041: Canonical JSON serialization + hardware-accelerated SHA-256.
//! Target: < 500ns per 1KB payload.

use sha2::{Digest, Sha256};

/// Canonical JSON serialization: sorted keys, no whitespace.
/// Mirrors Python `json.dumps(sort_keys=True, separators=(",",":"))`.
pub fn canonical_serialize(value: &serde_json::Value) -> String {
    match value {
        serde_json::Value::Object(map) => {
            let mut keys: Vec<&String> = map.keys().collect();
            keys.sort();
            let entries: Vec<String> = keys
                .iter()
                .map(|k| {
                    let v = canonical_serialize(&map[*k]);
                    format!("\"{}\":{}", k, v)
                })
                .collect();
            format!("{{{}}}", entries.join(","))
        }
        serde_json::Value::Array(arr) => {
            let items: Vec<String> = arr.iter().map(|v| canonical_serialize(v)).collect();
            format!("[{}]", items.join(","))
        }
        serde_json::Value::String(s) => format!("\"{}\"", s),
        serde_json::Value::Number(n) => n.to_string(),
        serde_json::Value::Bool(b) => b.to_string(),
        serde_json::Value::Null => "null".to_string(),
    }
}

/// SHA-256 CORTEX-TAINT of a canonical JSON string.
pub fn cortex_taint(canonical_json: &str) -> String {
    let mut hasher = Sha256::new();
    hasher.update(canonical_json.as_bytes());
    format!("{:x}", hasher.finalize())
}

/// Combined: serialize → taint. Returns (canonical_json, taint_hash).
pub fn taint_mutation(mutation: &serde_json::Value) -> (String, String) {
    let canonical = canonical_serialize(mutation);
    let hash = cortex_taint(&canonical);
    (canonical, hash)
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn test_canonical_deterministic() {
        let a = json!({"z": 1, "a": 2, "m": [3, 1]});
        let b = json!({"a": 2, "m": [3, 1], "z": 1});
        assert_eq!(canonical_serialize(&a), canonical_serialize(&b));
        assert_eq!(canonical_serialize(&a), r#"{"a":2,"m":[3,1],"z":1}"#);
    }

    #[test]
    fn test_taint_sha256() {
        let input = r#"{"a":1,"b":2}"#;
        let hash = cortex_taint(input);
        // SHA-256 of the literal string — deterministic across runs.
        assert_eq!(hash.len(), 64);
        // Verify idempotency.
        assert_eq!(hash, cortex_taint(input));
    }

    #[test]
    fn test_taint_mutation_roundtrip() {
        let val = json!({"origin": "crystallizer", "logic": "test"});
        let (json_str, hash) = taint_mutation(&val);
        assert!(json_str.contains("\"logic\":\"test\""));
        assert!(json_str.contains("\"origin\":\"crystallizer\""));
        // "logic" sorts before "origin"
        assert!(json_str.find("logic").unwrap() < json_str.find("origin").unwrap());
        assert_eq!(hash.len(), 64);
    }

    #[test]
    fn test_nested_canonical() {
        let val = json!({"b": {"z": 1, "a": 2}, "a": [3, {"y": 0, "x": 1}]});
        let s = canonical_serialize(&val);
        assert_eq!(s, r#"{"a":[3,{"x":1,"y":0}],"b":{"a":2,"z":1}}"#);
    }
}
