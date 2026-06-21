#![no_main]

use libfuzzer_sys::fuzz_target;
use cortex_ledger::{Block, Ledger};

fuzz_target!(|data: &[u8]| {
    let mut ledger = Ledger::new();
    let mut parent = [0u8; 32];
    let mut state = [0u8; 32];
    let mut proof = [0u8; 32];

    for (i, b) in data.iter().enumerate().take(32) {
        state[i] = *b;
    }

    for (i, b) in data.iter().enumerate().skip(32).take(32) {
        proof[i - 32] = *b;
    }

    let origin = String::from_utf8_lossy(data).chars().take(16).collect::<String>();
    let block = Block {
        parent_root: parent,
        state_hash: state,
        proof_hash: proof,
        origin,
        energy: data.len() as u64,
    };

    let _ = ledger.append(block);
});
