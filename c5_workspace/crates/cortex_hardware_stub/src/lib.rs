use cortex_types::{hash_bytes, hex32};

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct BoundaryToken {
    pub node_id: String,
    pub state_hash: [u8; 32],
    pub signature: [u8; 32],
}

const ROOT_KEY: &[u8] = b"c5-real-hardware-boundary-root-key";

pub fn attest(node_id: &str, state_hash: [u8; 32]) -> BoundaryToken {
    let mut payload = Vec::new();
    payload.extend_from_slice(ROOT_KEY);
    payload.extend_from_slice(node_id.as_bytes());
    payload.extend_from_slice(&state_hash);

    BoundaryToken {
        node_id: node_id.to_string(),
        state_hash,
        signature: hash_bytes(&payload),
    }
}

pub fn verify(token: &BoundaryToken) -> bool {
    let expected = attest(&token.node_id, token.state_hash);
    expected.signature == token.signature
}

pub fn label(token: &BoundaryToken) -> String {
    format!("{}:{}", token.node_id, hex32(&token.state_hash))
}
