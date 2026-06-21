use cortex_types::{hash_u64s, Event};

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ParseError {
    Empty,
}

pub fn generate_event(seed: u64, epoch: u64, index: u64) -> Option<Event> {
    let h = hash_u64s(&[seed, epoch, index]);
    let v = u64::from_le_bytes(h[0..8].try_into().expect("slice length"));

    match v % 10_000 {
        0 => Some(Event::LedgerForkCascade),
        1 => Some(Event::ZkCollisionAttempt),
        2 => Some(Event::FfiOverflowSpike),
        3 => Some(Event::CollapseThresholdOscillation),
        4 => Some(Event::ConcurrencySingularity),
        _ => None,
    }
}

pub fn stream_events(seed: u64, epoch: u64, n: u64) -> impl Iterator<Item = (u64, Event)> {
    (0..n).filter_map(move |index| generate_event(seed, epoch, index).map(|e| (index, e)))
}

pub fn parse_ir(ir: &str) -> Result<Event, ParseError> {
    let upper = ir.trim().to_ascii_uppercase();
    if upper.is_empty() {
        return Err(ParseError::Empty);
    }

    if upper.contains("FORK") {
        Ok(Event::LedgerForkCascade)
    } else if upper.contains("ZK") {
        Ok(Event::ZkCollisionAttempt)
    } else if upper.contains("OOM") || upper.contains("OVERFLOW") {
        Ok(Event::FfiOverflowSpike)
    } else if upper.contains("COLLAPSE") {
        Ok(Event::CollapseThresholdOscillation)
    } else if upper.contains("RACE") {
        Ok(Event::ConcurrencySingularity)
    } else {
        Ok(Event::Unknown(ir.to_string()))
    }
}
