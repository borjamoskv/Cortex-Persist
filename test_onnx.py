from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2", backend="onnx")
print("Model loaded with ONNX backend")
print(model.encode("Hello world"))
