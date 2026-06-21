use crate::mee::event::TransferEvent;
use crate::mee::state::Account;

/// The pure deterministic execution layer (C5-REAL Runtime).
/// It has no external I/O, network, or clock dependencies.
pub fn apply(state: &Account, event: &TransferEvent) -> Account {
    Account {
        balance: state.balance + event.delta,
    }
}
