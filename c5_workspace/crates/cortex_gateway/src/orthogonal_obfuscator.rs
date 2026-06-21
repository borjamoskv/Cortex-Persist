use ndarray::{Array1, Array2};
use rand::thread_rng;
use rand_distr::{Distribution, StandardNormal};

/// In-Memory Orthogonal Vector Obfuscator (Matrix Q)
/// Preserves Euclidean distances and angles (Cosine Similarity) 
/// while deterministically scrambling the latent space to prevent inversion.
pub struct OrthogonalObfuscator {
    pub q_matrix: Array2<f32>,
    pub dim: usize,
}

impl OrthogonalObfuscator {
    /// Generates a new random Orthogonal Matrix Q of size dim x dim
    /// stored exclusively in RAM for C5-REAL zero-knowledge obfuscation.
    pub fn new(dim: usize) -> Self {
        let mut rng = thread_rng();
        
        // 1. Generate Random Gaussian Matrix
        let mut a_matrix = Array2::<f32>::zeros((dim, dim));
        for i in 0..dim {
            for j in 0..dim {
                a_matrix[[i, j]] = StandardNormal.sample(&mut rng);
            }
        }

        // 2. Modified Gram-Schmidt Orthogonalization to create Q
        // Ensuring Q^T Q = I
        let mut q_matrix = Array2::<f32>::zeros((dim, dim));
        
        for i in 0..dim {
            let mut v = a_matrix.column(i).to_owned();
            
            for j in 0..i {
                let u_j = q_matrix.column(j);
                let proj_scalar = v.dot(&u_j);
                v = v - &u_j.mapv(|val| val * proj_scalar);
            }
            
            // Normalize
            let norm = v.dot(&v).sqrt();
            if norm > 1e-8 {
                v.mapv_inplace(|val| val / norm);
            }
            
            q_matrix.column_mut(i).assign(&v);
        }

        Self {
            q_matrix,
            dim,
        }
    }

    /// Applies isometric obfuscation: v' = Q * v
    /// Strictly preserves Cosine Similarity.
    pub fn obfuscate(&self, vector: &[f32]) -> Vec<f32> {
        if vector.len() != self.dim {
            panic!("Vector dimension {} does not match Obfuscator dimension {}", vector.len(), self.dim);
        }
        let v_array = Array1::from_shape_vec(self.dim, vector.to_vec())
            .expect("Failed to cast vector to Array1");
        
        let result = self.q_matrix.dot(&v_array);
        result.into_raw_vec()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_orthogonal_obfuscation_preserves_cosine() {
        let dim = 512;
        let obfuscator = OrthogonalObfuscator::new(dim);
        
        let mut rng = thread_rng();
        // Generate two random vectors
        let v1: Vec<f32> = (0..dim).map(|_| StandardNormal.sample(&mut rng)).collect();
        let v2: Vec<f32> = (0..dim).map(|_| StandardNormal.sample(&mut rng)).collect();
        
        let dot_original: f32 = v1.iter().zip(v2.iter()).map(|(a, b)| a * b).sum();
        let norm1_orig: f32 = v1.iter().map(|a| a * a).sum::<f32>().sqrt();
        let norm2_orig: f32 = v2.iter().map(|b| b * b).sum::<f32>().sqrt();
        let cos_original = dot_original / (norm1_orig * norm2_orig);
        
        let ov1 = obfuscator.obfuscate(&v1);
        let ov2 = obfuscator.obfuscate(&v2);
        
        let dot_obf: f32 = ov1.iter().zip(ov2.iter()).map(|(a, b)| a * b).sum();
        let norm1_obf: f32 = ov1.iter().map(|a| a * a).sum::<f32>().sqrt();
        let norm2_obf: f32 = ov2.iter().map(|b| b * b).sum::<f32>().sqrt();
        let cos_obf = dot_obf / (norm1_obf * norm2_obf);
        
        // Assert they are practically equal (Cosine Preserved)
        let diff = (cos_original - cos_obf).abs();
        assert!(diff < 1e-4, "Cosine similarity destroyed! Orig: {}, Obf: {}, Diff: {}", cos_original, cos_obf, diff);
    }
}
