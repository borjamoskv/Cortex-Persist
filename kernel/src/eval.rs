use crate::state::{MachineState, RegisterCell};
use crate::isa::{Instruction, Opcode, Value};

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum HaltReason {
    Graceful,
    Critical,
}

/// The pure transition function mathematically guarantees no runtime panics.
/// Dynamic array out-of-bounds are irrepresentable.
pub fn step(mut state: MachineState, instr: &Instruction) -> Result<MachineState, HaltReason> {
    state.logical_clock = state.logical_clock.tick();
    
    match &instr.opcode {
        Opcode::Alloc(reg, tag) => {
            let mut cell = state.read_reg(*reg).clone();
            cell.tag = *tag;
            state.write_reg(*reg, cell);
        }
        Opcode::LoadImm(reg, val) => {
            let mut cell = state.read_reg(*reg).clone();
            cell.value = Value::ImmI64(*val);
            state.write_reg(*reg, cell);
        }
        Opcode::Mov(dest, src) => {
            let cell = state.read_reg(*src).clone();
            state.write_reg(*dest, cell);
        }
        Opcode::Halt => return Err(HaltReason::Graceful),
        Opcode::CriticalHalt => return Err(HaltReason::Critical),
        // Additional pure operations here
        _ => {}
    }
    
    state.pc = state.pc.saturating_add(1);
    Ok(state)
}
