use rusqlite::{Connection, Result};
use std::path::Path;
use crate::orthogonal_obfuscator::OrthogonalObfuscator;

pub struct SqliteVecEngine {
    conn: Connection,
    obfuscator: OrthogonalObfuscator,
}

impl SqliteVecEngine {
    /// Initializes an in-memory or persisted SQLite instance and loads the sqlite-vec extension.
    /// Used for sub-millisecond retrieval of divergence boundaries.
    pub fn new(db_path: Option<&Path>, vec_ext_path: &Path) -> Result<Self> {
        let conn = match db_path {
            Some(path) => Connection::open(path)?,
            None => Connection::open_in_memory()?,
        };

        // Enable loading extensions
        // Safety: We control the extension path being loaded.
        unsafe {
            conn.load_extension_enable()?;
            conn.load_extension(vec_ext_path, None)?;
            conn.load_extension_disable()?;
        }

        // Initialize Virtual Tables for sqlite-vec
        conn.execute(
            "CREATE VIRTUAL TABLE IF NOT EXISTS divergence_embeddings USING vec0(
                embedding float[512]
            );",
            [],
        )?;

        let obfuscator = OrthogonalObfuscator::new(512);

        Ok(Self { conn, obfuscator })
    }

    /// Stores a new embedding into the sqlite-vec space
    pub fn insert_embedding(&self, vector: &[f32]) -> Result<i64> {
        let obf_vec = self.obfuscator.obfuscate(vector);
        // We encode the vector into bytes as expected by sqlite-vec
        let vector_bytes: Vec<u8> = obf_vec.iter().flat_map(|&f| f.to_ne_bytes()).collect();

        self.conn.execute(
            "INSERT INTO divergence_embeddings(embedding) VALUES (?1)",
            [rusqlite::types::Value::Blob(vector_bytes)],
        )?;

        Ok(self.conn.last_insert_rowid())
    }

    /// Performs Cosine Similarity lookup (ANN/KNN via sqlite-vec)
    pub fn find_nearest_cosine_divergence(&self, query_vector: &[f32], k: usize) -> Result<Vec<(i64, f64)>> {
        let obf_vec = self.obfuscator.obfuscate(query_vector);
        let vector_bytes: Vec<u8> = obf_vec.iter().flat_map(|&f| f.to_ne_bytes()).collect();

        let mut stmt = self.conn.prepare(
            "SELECT rowid, vec_distance_cosine(embedding, ?1) as distance 
             FROM divergence_embeddings 
             ORDER BY distance ASC 
             LIMIT ?2"
        )?;

        let rows = stmt.query_map(
            rusqlite::params![rusqlite::types::Value::Blob(vector_bytes), k],
            |row| Ok((row.get(0)?, row.get(1)?))
        )?;

        let mut results = Vec::new();
        for r in rows {
            results.push(r?);
        }

        Ok(results)
    }
}
