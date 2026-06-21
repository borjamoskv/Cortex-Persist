use tract_onnx::prelude::*;
use std::path::Path;

pub struct OnnxEmbeddingEngine {
    model: SimplePlan<TypedFact, Box<dyn TypedOp>, Graph<TypedFact, Box<dyn TypedOp>>>,
}

impl OnnxEmbeddingEngine {
    /// Loads a static ONNX encoder (e.g., nomic-embed-text-v1.5) into CPU memory.
    /// This runs entirely locally within the C5-REAL Hot Path, avoiding HTTP roundtrips.
    pub fn new<P: AsRef<Path>>(model_path: P) -> TractResult<Self> {
        let model = tract_onnx::onnx()
            .model_for_path(model_path)?
            // Adjust input dimensions according to the target encoder
            .with_input_fact(0, f32::fact(&[1, 512]).into())?
            .into_optimized()?
            .into_runnable()?;

        Ok(Self { model })
    }

    /// Extracts embeddings directly inside the Rust Hot Path
    pub fn encode(&self, input_tensor: Tensor) -> TractResult<Vec<f32>> {
        // Run inference
        let result = self.model.run(tvec!(input_tensor.into()))?;
        
        // Extract the vector representation (assuming output 0 is the embedding)
        let embedding_view = result[0].to_array_view::<f32>()?;
        
        // Convert to standard vector
        Ok(embedding_view.iter().copied().collect())
    }
}
