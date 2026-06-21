use cortex_hardware_stub as hardware;
use cortex_chaos::generate_event;
use cortex_rs::KernelTrait;
use cortex_types::{hex32, hash_bytes, ReplayUniverse, TraceStats, UniverseReport};

#[derive(Clone, Debug)]
pub struct UniverseOutcome {
    pub universe: ReplayUniverse,
    pub stats: TraceStats,
    pub attestation: String,
}

pub struct ReplayEngine<K: KernelTrait + Clone> {
    pub kernel_factory: fn() -> K,
}

impl<K: KernelTrait + Clone> ReplayEngine<K> {
    pub fn run_universe(&self, seed: u64, epoch: u64, n: u64) -> UniverseOutcome {
        let mut kernel = (self.kernel_factory)();
        let mut stats = TraceStats {
            events: n,
            ..TraceStats::default()
        };

        let mut event_digest = Vec::new();

        for index in 0..n {
            if let Some(event) = generate_event(seed, epoch, index) {
                event_digest.extend_from_slice(format!("{:?}", event).as_bytes());
                match kernel.apply_event(event) {
                    cortex_types::KernelResult::Accepted => stats.accepted += 1,
                    cortex_types::KernelResult::Rejected => stats.rejected += 1,
                    cortex_types::KernelResult::Collapse { .. } => {
                        stats.collapse = true;
                        stats.accepted += 1;
                        break;
                    }
                }
            }
        }

        stats.commits = if kernel.ledger_root() != [0u8; 32] { 1 } else { 0 };

        let universe = ReplayUniverse {
            seed,
            epoch,
            event_index: n,
            kernel_hash: kernel.kernel_hash(),
            ledger_root: kernel.ledger_root(),
        };

        let attestation = hardware::attest(
            &format!("replay:{}:{}", seed, epoch),
            hash_bytes(&event_digest),
        );

        UniverseOutcome {
            universe,
            stats,
            attestation: hardware::label(&attestation),
        }
    }

    pub fn report(&self, outcome: &UniverseOutcome) -> UniverseReport {
        UniverseReport {
            seed: outcome.universe.seed,
            epoch: outcome.universe.epoch,
            kernel_hash: hex32(&outcome.universe.kernel_hash),
            ledger_root: hex32(&outcome.universe.ledger_root),
            events: outcome.stats.events,
            accepted: outcome.stats.accepted,
            rejected: outcome.stats.rejected,
            collapse: outcome.stats.collapse,
            attestation: outcome.attestation.clone(),
        }
    }
}

pub fn divergence(a: &UniverseOutcome, b: &UniverseOutcome) -> u64 {
    let sa = format!(
        "{}:{}:{}:{}:{}",
        a.stats.accepted, a.stats.rejected, a.stats.commits, a.stats.collapse, a.stats.events
    );
    let sb = format!(
        "{}:{}:{}:{}:{}",
        b.stats.accepted, b.stats.rejected, b.stats.commits, b.stats.collapse, b.stats.events
    );

    let ha = hash_bytes(sa.as_bytes());
    let hb = hash_bytes(sb.as_bytes());

    let mut diff = 0u64;
    for i in 0..32 {
        diff = diff.wrapping_add((ha[i] ^ hb[i]) as u64);
    }
    diff
}
