#!/usr/bin/env python3
"""
agent_with_tools.py — C5-REAL ReAct Agent + RAG Codebase
Zero-dependency agent (ollama-python + chromadb).
Optimizado para M3 Pro 18GB: ingesta selectiva, chunks pequeños, k=3.
"""

import os
import re
import subprocess
from typing import Optional

import chromadb
import ollama

# ==================== CONFIG ====================
MODEL_CHAT = "qwen2.5-coder:7b"
CODEBASE_ROOT = "."
# Solo ingestar módulos core (evita 2000 archivos)
INGEST_DIRS = [
    "cortex/database",
    "cortex/pipeline",
    "cortex/consensus",
    "cortex/engine",
    "cortex/auth",
    "cortex/api",
    "cortex/cli",
]
CHUNK_SIZE = 500  # tokens aprox por chunk
TOP_K = 3
MAX_REACT_STEPS = 6

# ==================== RAG ====================

def chunk_code(code: str, max_tokens: int = CHUNK_SIZE) -> list[str]:
    """Chunking por bloques de líneas."""
    lines = code.split("\n")
    chunks, current, count = [], [], 0
    for line in lines:
        words = len(line.split())
        if count + words > max_tokens and current:
            chunks.append("\n".join(current))
            current, count = [], 0
        current.append(line)
        count += words
    if current:
        chunks.append("\n".join(current))
    return chunks


def build_vectorstore() -> chromadb.Collection:
    """Ingesta selectiva de .py en Chroma in-memory."""
    client = chromadb.Client()
    try:
        client.delete_collection("cortex")
    except Exception:
        pass
    col = client.create_collection("cortex")

    all_docs, all_ids, all_meta = [], [], []
    idx = 0

    for subdir in INGEST_DIRS:
        dirpath = os.path.join(CODEBASE_ROOT, subdir)
        if not os.path.isdir(dirpath):
            continue
        for root, _, files in os.walk(dirpath):
            for fname in files:
                if not fname.endswith(".py"):
                    continue
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        code = f.read()
                except Exception:
                    continue
                for chunk in chunk_code(code):
                    all_docs.append(chunk)
                    all_ids.append(f"c_{idx}")
                    all_meta.append({"source": fpath})
                    idx += 1

    if all_docs:
        # Chroma acepta batch de hasta 5461
        for i in range(0, len(all_docs), 5000):
            col.add(
                ids=all_ids[i : i + 5000],
                documents=all_docs[i : i + 5000],
                metadatas=all_meta[i : i + 5000],
            )
    return col


def retrieve(col: chromadb.Collection, query: str, k: int = TOP_K) -> str:
    """Retrieval con Chroma default embeddings."""
    results = col.query(query_texts=[query], n_results=k)
    if not results["documents"] or not results["documents"][0]:
        return "(Sin contexto relevante del codebase)"
    parts = []
    for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
        src = meta.get("source", "?")
        parts.append(f"# {src}\n{doc}")
    return "\n\n".join(parts)


# ==================== TOOLS ====================

def execute_bash(command: str) -> str:
    """Ejecuta un comando bash."""
    try:
        command = command.strip().strip("`").strip('"').strip("'")
        r = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=15)
        out = r.stdout.strip()
        err = r.stderr.strip()
        if err and not out:
            return f"STDERR:\n{err}"
        if err:
            return f"STDOUT:\n{out}\nSTDERR:\n{err}"
        return out or "(sin salida)"
    except subprocess.TimeoutExpired:
        return "Error: timeout (15s)"
    except Exception as e:
        return f"Error: {e}"


def execute_git(command: str) -> str:
    """Ejecuta un comando git."""
    command = command.strip()
    if not command.startswith("git"):
        command = f"git {command}"
    return execute_bash(command)


def execute_tests(command: str) -> str:
    """Ejecuta pytest."""
    command = command.strip()
    if not command:
        command = "pytest --tb=short -q"
    return execute_bash(command)


TOOLS = {
    "bash": ("Ejecuta comandos bash en el sistema local.", execute_bash),
    "git": ("Ejecuta comandos git (status, diff, log, etc.).", execute_git),
    "tests": ("Ejecuta tests del proyecto (pytest).", execute_tests),
}

TOOL_LIST = "\n".join(f"  - {name}: {desc}" for name, (desc, _) in TOOLS.items())

# ==================== REACT ====================

REACT_SYSTEM = """Eres KETER_LOCAL, un agente autónomo C5-REAL de programación.
Tienes acceso a estas herramientas:
{tools}

Formato OBLIGATORIO de respuesta:

Thought: (razonamiento paso a paso)
Action: (nombre de herramienta: bash | git | tests)
Action Input: (el comando exacto a ejecutar)

Cuando tengas la respuesta final:

Thought: Ya tengo la respuesta.
Final Answer: (respuesta concisa)

REGLAS:
- Cero narrativa decorativa.
- Action Input debe ser el comando exacto, sin markdown, sin comillas de código.
- Puedes usar el contexto del codebase para informar tus respuestas.
"""


def parse_react(text: str) -> dict:
    """Extrae Thought, Action, Action Input, Final Answer."""
    result = {}
    for key in ["Thought", "Action", "Action Input", "Final Answer"]:
        m = re.search(rf"{key}:\s*(.*?)(?=\n(?:Thought|Action|Final Answer)|$)", text, re.DOTALL | re.IGNORECASE)
        if m:
            result[key.lower().replace(" ", "_")] = m.group(1).strip()
    return result


def react_loop(query: str, col: chromadb.Collection) -> str:
    """Bucle ReAct con RAG retrieval."""
    context = retrieve(col, query)

    prompt = REACT_SYSTEM.format(tools=TOOL_LIST) + f"""
--- CONTEXTO CODEBASE ---
{context}
--- FIN CONTEXTO ---

Pregunta del usuario: {query}
"""
    messages = [{"role": "user", "content": prompt}]

    for step in range(MAX_REACT_STEPS):
        response = ollama.chat(model=MODEL_CHAT, messages=messages)
        content = response["message"]["content"]
        print(f"\n[STEP {step + 1}]\n{content}")
        messages.append({"role": "assistant", "content": content})

        parsed = parse_react(content)

        if "final_answer" in parsed:
            return parsed["final_answer"]

        action = parsed.get("action", "").strip().lower()
        action_input = parsed.get("action_input", "").strip()

        if action in TOOLS and action_input:
            print(f"  -> [{action.upper()}]: {action_input}")
            _, fn = TOOLS[action]
            observation = fn(action_input)
            print(f"  -> [OBS]: {observation[:500]}")
            messages.append({"role": "user", "content": f"Observation: {observation}"})
        else:
            messages.append({
                "role": "user",
                "content": "Observation: Formato inválido. Usa 'Action: bash' y 'Action Input: <comando>'.",
            })

    return "(Límite de pasos alcanzado sin respuesta final)"


# ==================== MAIN ====================

def main():
    print(f"[C5-REAL] ReAct Agent + RAG | Model: {MODEL_CHAT}")
    print("Ingestando codebase (módulos core)...")
    col = build_vectorstore()
    n = col.count()
    print(f"Ingestados {n} chunks de {len(INGEST_DIRS)} módulos.")
    print(f"Herramientas: {', '.join(TOOLS.keys())}")
    print("=" * 60)
    print("Escribe tu pregunta (q para salir):\n")

    while True:
        try:
            query = input(">>> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if query.lower() in ("q", "quit", "exit", ""):
            break
        answer = react_loop(query, col)
        print(f"\n{'=' * 60}")
        print(f"[FINAL]: {answer}")
        print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
