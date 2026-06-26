use crate::time::{SimulationClock, LogicalClock};
use crate::ledger::DAGLedger;
use crate::isa::{TypeTag, Value, Reg};

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RegisterCell {
    pub value: Value,
    pub tag: TypeTag,
}

impl RegisterCell {
    pub fn empty() -> Self {
        Self {
            value: Value::ImmI64(0),
            tag: TypeTag::Unallocated,
        }
    }
}

/// The MachineState is perfectly bounded. No dynamic vectors for registers.
/// 3 Registers exactly.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct MachineState {
    pub r1: RegisterCell,
    pub r2: RegisterCell,
    pub r3: RegisterCell,
    pub pc: usize,
    pub sim_clock: SimulationClock,
    pub logical_clock: LogicalClock,
    pub ledger: DAGLedger,
}

impl MachineState {
    pub fn new() -> Self {
        Self {
            r1: RegisterCell::empty(),
            r2: RegisterCell::empty(),
            r3: RegisterCell::empty(),
            pc: 0,
            sim_clock: SimulationClock::new(0),
            logical_clock: LogicalClock::new(0),
            ledger: DAGLedger::new(),
        }
    }

    pub fn read_reg(&self, reg: Reg) -> &RegisterCell {
        match reg {
            Reg::R1 => &self.r1,
            Reg::R2 => &self.r2,
            Reg::R3 => &self.r3,
        }
    }

    pub fn write_reg(&mut self, reg: Reg, cell: RegisterCell) {
        match reg {
            Reg::R1 => self.r1 = cell,
            Reg::R2 => self.r2 = cell,
            Reg::R3 => self.r3 = cell,
        }
    }
}
