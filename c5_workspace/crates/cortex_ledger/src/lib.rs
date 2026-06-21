use cortex_types::{hash_bytes, hash_u64s};

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Block {
    pub parent_root: [u8; 32],
    pub state_hash: [u8; 32],
    pub proof_hash: [u8; 32],
    pub origin: String,
    pub energy: u64,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum LedgerError {
    OrphanedBlock,
    EmptyOrigin,
}

#[derive(Clone, Debug, Default)]
pub struct Ledger {
    root: [u8; 32],
    blocks: Vec<Block>,
}

impl Ledger {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn root(&self) -> [u8; 32] {
        self.root
    }

    pub fn len(&self) -> usize {
        self.blocks.len()
    }

    pub fn append(&mut self, block: Block) -> Result<[u8; 32], LedgerError> {
        if block.origin.trim().is_empty() {
            return Err(LedgerError::EmptyOrigin);
        }

        if block.parent_root != self.root {
            return Err(LedgerError::OrphanedBlock);
        }

        let next_root = hash_bytes(&[
            self.root.as_slice(),
            block.state_hash.as_slice(),
            block.proof_hash.as_slice(),
            block.origin.as_bytes(),
            &hash_u64s(&[block.energy]),
        ]
        .concat());

        self.root = next_root;
        self.blocks.push(block);
        Ok(self.root)
    }

    pub fn blocks(&self) -> &[Block] {
        &self.blocks
    }
}
