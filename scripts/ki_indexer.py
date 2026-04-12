#!/usr/bin/env python3
import os
import glob
from sentence_transformers import SentenceTransformer
import chromadb

KNOWLEDGE_DIR = os.path.expanduser("~/.gemini/antigravity/knowledge")
DB_DIR = os.path.expanduser("~/.gemini/antigravity/chroma_db")

def main():
    print("CORTEX-Indexer: Inicializando motor O(1) de persistencia semántica...")
    
    # 1. Initialize Vector DB
    client = chromadb.PersistentClient(path=DB_DIR)
    collection = client.get_or_create_collection(
        name="cortex_knowledge",
        metadata={"hnsw:space": "cosine"}
    )
    
    # 2. Load Embedding Model
    print("CORTEX-Indexer: Cargando BAAI/bge-small-en-v1.5...")
    # BGE-small is extremely fast and effective for short to medium docs
    model = SentenceTransformer("BAAI/bge-small-en-v1.5")
    
    # 3. Harvest Knowledge Items
    ki_folders = glob.glob(os.path.join(KNOWLEDGE_DIR, "*"))
    
    docs = []
    metadatas = []
    ids = []
    
    for folder in ki_folders:
        overview_path = os.path.join(folder, "artifacts", "overview.md")
        if not os.path.exists(overview_path):
            continue
            
        folder_name = os.path.basename(folder)
        
        with open(overview_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Para evitar problemas con el size limits o ruido, truncamos razonablemente.
        # En caso de BGE-small la ventana es 512 tokens.
        content = content[:3000] # aprox truncamiento a ~600 tokens
        
        docs.append(content)
        metadatas.append({"folder": folder_name, "source": overview_path})
        ids.append(folder_name)
        
    if not docs:
        print("CORTEX-Indexer: No se encontraron Knowledge Items.")
        return

    print(f"CORTEX-Indexer: Computando embeddings para {len(docs)} vectores de conocimiento...")
    embeddings = model.encode(docs, normalize_embeddings=True).tolist()
    
    print("CORTEX-Indexer: Upserting en ChromaDB...")
    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=docs,
        metadatas=metadatas
    )
    
    print(f"CORTEX-Indexer: Indexación completada. {len(ids)} KIs persistidos correctamente (O(1) Yield).")

if __name__ == "__main__":
    main()
