use cortex_chaos::parse_ir;
use cortex_rs::{CortexKernel, KernelTrait};

#[derive(Clone, Debug)]
pub struct BoundaryKernel {
    inner: CortexKernel,
}

impl BoundaryKernel {
    pub fn new() -> Self {
        Self {
            inner: CortexKernel::new(),
        }
    }

    pub fn submit_ir(&mut self, ir: &str) -> String {
        if ir.contains('\0') {
            return "REJECTED".to_string();
        }
        let event = parse_ir(ir).unwrap_or(cortex_types::Event::Unknown(ir.to_string()));
        match self.inner.apply_event(event) {
            cortex_types::KernelResult::Accepted => "ACCEPTED".to_string(),
            cortex_types::KernelResult::Rejected => "REJECTED".to_string(),
            cortex_types::KernelResult::Collapse { reason } => format!("HARD_FAIL:{:?}", reason),
        }
    }

    pub fn state_hash(&self) -> String {
        cortex_types::hex32(&self.inner.state_hash())
    }

    pub fn ledger_root(&self) -> String {
        cortex_types::hex32(&self.inner.ledger_root())
    }
}
