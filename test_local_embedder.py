import os
from cortex.embeddings.local import LocalEmbedder

embedder = LocalEmbedder()
emb = embedder.embed("ONNX INT8 Speed test")
print(f"Embedding generated! Length: {len(emb)}, type: {type(emb[0])}")
