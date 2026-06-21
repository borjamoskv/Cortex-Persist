use cortex_types::{hash_bytes, Event};

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Proof {
    pub state_hash: [u8; 32],
    pub witness_hash: [u8; 32],
    pub valid: bool,
}

pub fn prove(event: &Event, state_hash: [u8; 32]) -> Proof {
    let witness_hash = hash_bytes(format!("{:?}", event).as_bytes());
    Proof {
        state_hash,
        witness_hash,
        valid: true,
    }
}

pub fn corrupt(mut proof: Proof) -> Proof {
    proof.valid = false;
    proof.witness_hash = [0u8; 32];
    proof
}

pub fn verify(proof: &Proof, event: &Event) -> bool {
    if !proof.valid {
        return false;
    }

    let expected_witness = hash_bytes(format!("{:?}", event).as_bytes());
    proof.witness_hash == expected_witness && proof.state_hash != [0u8; 32]
}
