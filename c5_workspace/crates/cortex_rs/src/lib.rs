use cortex_chaos::generate_event;
use cortex_hardware_stub as hardware;
use cortex_ledger::{Block, Ledger, LedgerError};
use cortex_types::{hash_bytes, hex32, CollapseReason, Event, KernelResult, E_CRIT};
use cortex_zk::{self, Proof};

pub trait KernelTrait: Clone {
    fn apply_event(&mut self, event: Event) -> KernelResult;
    fn collapse_detected(&self) -> bool;
    fn state_hash(&self) -> [u8; 32];
    fn ledger_root(&self) -> [u8; 32];
    fn kernel_hash(&self) -> [u8; 32];
}

#[derive(Clone, Debug)]
pub struct CortexKernel {
    node_id: String,
    energy: u64,
    collapsed: bool,
    state_hash: [u8; 32],
    ledger: Ledger,
}

impl Default for CortexKernel {
    fn default() -> Self {
        Self::new()
    }
}

impl CortexKernel {
    pub fn new() -> Self {
        Self {
            node_id: "cortex-node-0".to_string(),
            energy: 0,
            collapsed: false,
            state_hash: [0u8; 32],
            ledger: Ledger::new(),
        }
    }

    pub fn with_node_id(node_id: impl Into<String>) -> Self {
        let mut kernel = Self::new();
        kernel.node_id = node_id.into();
        kernel
    }

    fn kernel_hash_bytes() -> [u8; 32] {
        hash_bytes(b"cortex_rs::deterministic_kernel_v0.1")
    }

    fn collapse(&mut self, reason: CollapseReason) -> KernelResult {
        self.collapsed = true;
        KernelResult::Collapse { reason }
    }

    fn commit_event(&mut self, event: &Event) -> Result<(), KernelResult> {
        let mut state_input = Vec::new();
        state_input.extend_from_slice(&self.state_hash);
        state_input.extend_from_slice(format!("{:?}", event).as_bytes());
        state_input.extend_from_slice(&self.energy.to_le_bytes());
        self.state_hash = hash_bytes(&state_input);

        let proof: Proof = cortex_zk::prove(event, self.state_hash);
        let proof_hash = hash_bytes(format!("{:?}", proof).as_bytes());

        let token = hardware::attest(&self.node_id, self.state_hash);
        if !hardware::verify(&token) {
            return Err(self.collapse(CollapseReason::MemoryViolation));
        }

        let block = Block {
            parent_root: self.ledger.root(),
            state_hash: self.state_hash,
            proof_hash,
            origin: self.node_id.clone(),
            energy: self.energy,
        };

        match self.ledger.append(block) {
            Ok(_) => Ok(()),
            Err(LedgerError::OrphanedBlock) => Err(self.collapse(CollapseReason::LedgerForkAccepted)),
            Err(LedgerError::EmptyOrigin) => Err(self.collapse(CollapseReason::MemoryViolation)),
        }
    }

    pub fn submit_ir(&mut self, ir: &str) -> KernelResult {
        let event = cortex_chaos::parse_ir(ir).unwrap_or(Event::Unknown(ir.to_string()));
        self.apply_event(event)
    }
}

impl KernelTrait for CortexKernel {
    fn apply_event(&mut self, event: Event) -> KernelResult {
        if self.collapsed {
            return self.collapse(CollapseReason::MemoryViolation);
        }

        match event {
            Event::LedgerForkCascade => return self.collapse(CollapseReason::LedgerForkAccepted),
            Event::ZkCollisionAttempt => {
                let proof = cortex_zk::corrupt(cortex_zk::prove(&Event::ZkCollisionAttempt, self.state_hash));
                if !cortex_zk::verify(&proof, &Event::ZkCollisionAttempt) {
                    return self.collapse(CollapseReason::ZkAcceptedInvalidProof);
                }
                self.energy = self.energy.saturating_add(1000);
            }
            Event::FfiOverflowSpike => {
                self.energy = self.energy.saturating_add(4_000);
            }
            Event::CollapseThresholdOscillation => {
                self.energy = self.energy.saturating_add(500);
            }
            Event::ConcurrencySingularity => {
                self.energy = self.energy.saturating_add(250);
            }
            Event::Unknown(_) => {
                self.energy = self.energy.saturating_add(1);
            }
        }

        if self.energy > E_CRIT {
            return self.collapse(CollapseReason::EnergyExceeded);
        }

        if let Err(result) = self.commit_event(&event) {
            return result;
        }

        KernelResult::Accepted
    }

    fn collapse_detected(&self) -> bool {
        self.collapsed
    }

    fn state_hash(&self) -> [u8; 32] {
        self.state_hash
    }

    fn ledger_root(&self) -> [u8; 32] {
        self.ledger.root()
    }

    fn kernel_hash(&self) -> [u8; 32] {
        Self::kernel_hash_bytes()
    }
}

pub fn deterministically_apply(seed: u64, epoch: u64, index: u64, kernel: &mut CortexKernel) -> KernelResult {
    if let Some(event) = generate_event(seed, epoch, index) {
        kernel.apply_event(event)
    } else {
        KernelResult::Rejected
    }
}

pub fn kernel_hash_hex() -> String {
    hex32(&CortexKernel::kernel_hash_bytes())
}
