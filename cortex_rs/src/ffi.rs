use serde_json::Value;
use std::sync::{Arc, RwLock, OnceLock};

static LEDGER_STATE: OnceLock<Arc<RwLock<Vec<Value>>>> = OnceLock::new();

pub fn submit_ir(ir: &str) -> Result<String, String> {
    // Phase I: FFI Membrane Assault
    if ir.contains('\0') || ir.contains("\\u0000") {
        return Err("REJECTED_POISONED_IR".to_string());
    }
    
    if ir.len() > 1024 * 64 {
        return Err("REJECTED_OVERSIZED_PAYLOAD".to_string());
    }

    let parsed: Result<Value, _> = serde_json::from_str(ir);
    match parsed {
        Ok(v) => {
            let state = LEDGER_STATE.get_or_init(|| Arc::new(RwLock::new(Vec::new())));
            if let Ok(mut lock) = state.write() {
                lock.push(v);
            }
            Ok("hash-placeholder".to_string())
        }
        Err(_) => Err("REJECTED_MALFORMED_JSON".to_string()),
    }
}
