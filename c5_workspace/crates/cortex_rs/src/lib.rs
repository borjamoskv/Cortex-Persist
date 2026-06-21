pub fn submit_ir(ir: &str) -> Result<String, String> {
    // Stub implementation for now
    Ok(format!("HASH_{}", ir.len()))
}

pub fn get_ledger_root() -> Result<String, String> {
    Ok("ROOT_HASH_STUB".to_string())
}
