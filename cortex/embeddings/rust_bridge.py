# [C5-REAL] Exergy-Maximized
"""CORTEX v6+ - Rust-Native Embeddings Bridge.

Bypasses the Python GIL by delegating tensor operations to ONNX Runtime
(C++/Rust native backend). Enforces parallel execution and zero emulation.
"""

import logging
import os
import sys

try:
    import onnxruntime as ort
except ImportError:
    if not os.environ.get("CORTEX_TESTING"):
        # Hard Fail: C5-REAL INV_ZERO_EMULATION
        # We do NOT fallback to PyTorch stochastic emulation.
        logging.critical("[INV_ZERO_EMULATION] onnxruntime missing. Pure Python emulation forbidden. CRASHING.")
        sys.exit(1)
    else:
        ort = None

# In a real environment, we would use huggingface `tokenizers` library which is Rust-native
try:
    from tokenizers import Tokenizer
except ImportError:
    Tokenizer = None

logger = logging.getLogger("cortex.embeddings.rust_bridge")

class RustNativeEmbeddings:
    """Provides Exergy-maximized dense vector generation via ONNX/Rust bindings."""
    
    def __init__(self, model_path: str, tokenizer_path: str):
        self.model_path = model_path
        self.tokenizer_path = tokenizer_path
        
        # Enforce Native Backend Execution
        if not os.path.exists(model_path) and not os.environ.get("CORTEX_TESTING"):
            logger.error(f"[RustBridge] ONNX model missing at {model_path}")
            raise FileNotFoundError(f"ONNX model not found: {model_path}")
            
        # Configure Parallelism to maximize thermodynamic efficiency
        sess_options = ort.SessionOptions()
        sess_options.intra_op_num_threads = os.cpu_count() or 4
        sess_options.execution_mode = ort.ExecutionMode.ORT_PARALLEL
        sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        
        if not os.environ.get("CORTEX_TESTING"):
            self.session = ort.InferenceSession(
                model_path, 
                sess_options, 
                providers=['CPUExecutionProvider']
            )
            if Tokenizer:
                self.tokenizer = Tokenizer.from_file(tokenizer_path)
            else:
                self.tokenizer = None
        else:
            self.session = None
            self.tokenizer = None
            
        logger.info(f"[RustBridge] Initialized ONNX Native Backend for {model_path}")
        
    def generate(self, texts: list[str]) -> list[list[float]]:
        """
        Tokenize and execute the model forward pass via the native C++ API.
        """
        if not texts:
            return []
            
        # Mocking for tests to prevent downloading massive weights
        if os.environ.get("CORTEX_TESTING"):
            import numpy as np
            # Simulate a 384-dimensional dense vector
            return np.random.rand(len(texts), 384).tolist()
            
        if not self.tokenizer:
            raise RuntimeError("tokenizers package required for real inference")
            
        # 1. Tokenization (Rust Native)
        encoded = self.tokenizer.encode_batch(texts)
        
        input_ids = [e.ids for e in encoded]
        attention_mask = [e.attention_mask for e in encoded]
        
        import numpy as np
        
        # 2. Execution (C++ Native)
        ort_inputs = {
            "input_ids": np.array(input_ids, dtype=np.int64),
            "attention_mask": np.array(attention_mask, dtype=np.int64),
        }
        
        # Typically the output is 'last_hidden_state' or 'sentence_embedding'
        ort_outs = self.session.run(None, ort_inputs)
        
        # Mean pooling based on attention mask
        embeddings = ort_outs[0]  # shape: (batch_size, seq_len, hidden_size)
        
        mask_expanded = np.expand_dims(np.array(attention_mask), -1)
        sum_embeddings = np.sum(embeddings * mask_expanded, axis=1)
        sum_mask = np.clip(np.sum(mask_expanded, axis=1), a_min=1e-9, a_max=None)
        
        pooled = sum_embeddings / sum_mask
        
        # L2 Normalization
        norms = np.linalg.norm(pooled, axis=1, keepdims=True)
        normalized = pooled / norms
        
        return normalized.tolist()
