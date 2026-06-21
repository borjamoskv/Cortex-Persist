use cortex_chaos::generate_event;
use cortex_types::{hash_u64s, Event};

#[no_mangle]
pub extern "C" fn cortex_wasm_digest(seed: u64, epoch: u64, n: u64) -> u64 {
    let mut acc = 0u64;

    for i in 0..n {
        if let Some(event) = generate_event(seed, epoch, i) {
            let tag = match event {
                Event::LedgerForkCascade => 1,
                Event::ZkCollisionAttempt => 2,
                Event::FfiOverflowSpike => 3,
                Event::CollapseThresholdOscillation => 4,
                Event::ConcurrencySingularity => 5,
                Event::Unknown(_) => 0,
            };
            let h = hash_u64s(&[seed, epoch, i, tag]);
            acc ^= u64::from_le_bytes(h[0..8].try_into().expect("slice length"));
        }
    }

    acc
}
