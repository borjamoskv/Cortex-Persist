use blake3::Hasher;
use quote::ToTokens;
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::Path;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EvidenceHash {
    pub commit_hash: String,
    pub ast_hash: Option<String>,
}

impl EvidenceHash {
    pub fn new(commit_hash: String, ast_hash: Option<String>) -> Self {
        Self {
            commit_hash,
            ast_hash,
        }
    }
}

/// Generates a semantic structural hash of a Rust file's AST.
/// Uses `syn` to parse the AST, then `quote` to convert it back into a canonical token stream.
/// Finally hashes the token stream using BLAKE3. This ignores comments and formatting.
pub fn hash_rust_file_ast<P: AsRef<Path>>(file_path: P) -> Result<String, anyhow::Error> {
    let content = fs::read_to_string(file_path)?;
    let syntax_tree = syn::parse_file(&content)?;

    // Canonicalize by converting the AST back to a token stream
    // This removes all whitespace, formatting, and comments from the hash computation.
    let tokens = syntax_tree.into_token_stream();
    let token_string = tokens.to_string();

    let mut hasher = Hasher::new();
    hasher.update(token_string.as_bytes());
    let hash = hasher.finalize();

    Ok(hash.to_hex().to_string())
}

/// Helper to generate a deterministic Merkle root over a set of Rust file AST hashes.
/// The hashes are sorted lexicographically before hashing to ensure determinism.
pub fn merkle_hash_asts(file_paths: &[&Path]) -> Result<String, anyhow::Error> {
    let mut file_hashes = Vec::new();
    for &path in file_paths {
        let hash = hash_rust_file_ast(path)?;
        file_hashes.push(hash);
    }

    // Sort hashes to ensure deterministic construction regardless of file order
    file_hashes.sort();

    let mut hasher = Hasher::new();
    for hash in file_hashes {
        hasher.update(hash.as_bytes());
    }

    Ok(hasher.finalize().to_hex().to_string())
}
