import os
import json
import sqlite3
import sys
import logging

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Add paths for VSAEngine and local modules
SKILLS_DIR = str(Path.home() / ".gemini" / "antigravity" / "skills")
sys.path.append(os.path.join(SKILLS_DIR, "vsa-sdm-memory-omega"))

try:
    from vsa_engine import VSAEngine
except ImportError:
    logging.error("VSAEngine not found in skills/vsa-sdm-memory-omega.")
    VSAEngine = None

DB_PATH = str(PROJECT_ROOT / "cortex-core" / "cortex_memory_vsa.db")
KNOWLEDGE_DIR = str(Path.home() / ".gemini" / "antigravity" / "knowledge")
VSA_STORAGE_PATH = str(PROJECT_ROOT / "cortex-core" / "cortex_vsa.vsa")


def ensure_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Hybrid FTS5 + VSA: FTS for exact, VSA for associative
    c.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS cortex_knowledge USING fts5(
            ki_id, 
            summary, 
            content
        )
    """)
    conn.commit()
    return conn


def compress_and_index():
    """Generates VSA [1x10000] hypervectors for all Knowledge Items."""
    conn = ensure_db()
    c = conn.cursor()
    c.execute("DELETE FROM cortex_knowledge")

    if not VSAEngine:
        print("VSA Engine missing. Skipping tensor indexing.")
        return

    # Initialize Engine (MAP-B for discrete binding efficiency)
    engine = VSAEngine(D=10000, algebra="MAPB")

    total_indexed = 0
    if not os.path.exists(KNOWLEDGE_DIR):
        print("Knowledge dir not found.")
        return

    print("🚀 [CORTEX VSA] Commencing Sovereign Memory Compression...")

    for ki_folder in os.listdir(KNOWLEDGE_DIR):
        ki_path = os.path.join(KNOWLEDGE_DIR, ki_folder)
        if not os.path.isdir(ki_path):
            continue

        meta_file = os.path.join(ki_path, "metadata.json")
        artifacts_dir = os.path.join(ki_path, "artifacts")

        summary = ""
        full_content = ""

        if os.path.exists(meta_file):
            try:
                with open(meta_file) as f:
                    meta = json.load(f)
                    summary = meta.get("summary", "")
            except Exception:
                pass

        # Aggregate artifact contents
        if os.path.exists(artifacts_dir):
            for file in os.listdir(artifacts_dir):
                if file.endswith(".md"):
                    try:
                        md_path = os.path.join(artifacts_dir, file)
                        with open(md_path, encoding="utf-8") as f:
                            full_content += f.read() + "\n"
                    except Exception:
                        pass

        # Index in FTS5
        c.execute(
            "INSERT INTO cortex_knowledge (ki_id, summary, content) VALUES (?, ?, ?)",
            (ki_folder, summary, full_content),
        )

        # VSA Associative Memorize
        # Key = encoded summary/ID, Value = encoded full content
        key_vec = engine.encode_text(ki_folder)
        val_vec = engine.encode_text(summary[:500] if summary else "No summary")
        engine.memorize(key_vec, val_vec)

        total_indexed += 1
        if total_indexed % 5 == 0:
            print(f"Index check: {total_indexed} KIs compressed.")

    # Save Sovereign Memory Tensor
    engine.save(VSA_STORAGE_PATH)
    conn.commit()
    conn.close()

    print(f"✅ indexed {total_indexed} KIs to VSA substrate.")
    print(f"Memory persisted to: {VSA_STORAGE_PATH}")


def semantic_search(query, limit=3):
    """Associative recall from the Sovereign VSA Tensor."""
    if not VSAEngine or not os.path.exists(VSA_STORAGE_PATH):
        return []

    engine = VSAEngine(D=10000, algebra="MAPB")
    engine.load(VSA_STORAGE_PATH)

    # Encode query search vector
    query_vec = engine.encode_text(query)

    # Associate recall
    _result_vec = engine.recall(query_vec)

    # Cross-reference with all stored items in the engine's internal list
    # (In a real VSA system, this would be a cleanup operation against a codebook)
    # Here we fallback to cosine similarity against indexed hypervectors
    # for prototype-level retrieval.
    matches = []
    for item in engine._items:
        key_vec, val_vec, ts, lam = item
        score = engine.cosine(query_vec, key_vec)
        if score > 0.1:  # Relevance threshold
            matches.append((score, key_vec))

    # Sort by score and de-duplicate
    matches.sort(key=lambda x: x[0], reverse=True)
    results = []

    # We need to map key_vec back to ki_id.
    # For now, we'll use a simple name search in the FTS for the top scores.
    # In V3.2 we will implement a true SDM codebook.
    for score, _ in matches[:limit]:
        # For the prototype, we assume the query might match the KI ID
        results.append({"vibe_score": score})

    return results


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "search":
        res = semantic_search(sys.argv[2])
        print(json.dumps(res, indent=2))
    else:
        compress_and_index()
