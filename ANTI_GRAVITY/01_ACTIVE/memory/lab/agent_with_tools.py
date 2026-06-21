#!/usr/bin/env python3
"""
agent_with_tools.py — C5-REAL ReAct Agent + Local BM25 RAG Codebase
Zero-dependency agent (ollama-python + math/re).
Optimizado para M3 Pro 18GB: 100% local, VRAM cero, indexación instantánea.
"""

import math
import os
import re
import subprocess
from collections import Counter

import ollama

# ==================== CONFIG ====================
MODEL_CHAT = "qwen2.5-coder:7b"
CODEBASE_ROOT = "."
# Módulos core a indexar
INGEST_DIRS = [
    "cortex/database",
    "cortex/pipeline",
    "cortex/consensus",
    "cortex/engine",
    "cortex/auth",
    "cortex/api",
    "cortex/cli",
]
CHUNK_SIZE = 500  # tokens/palabras aprox por chunk
TOP_K = 3
MAX_REACT_STEPS = 6

# ==================== BM25 ENGINE ====================

class SimpleBM25:
    """Motor BM25 ultraligero y rápido para búsqueda en código sin dependencias ni VRAM."""
    def __init__(self, documents: list[str], metadatas: list[dict], b: float = 0.75, k1: float = 1.5):
        self.documents = documents
        self.metadatas = metadatas
        self.b = b
        self.k1 = k1
        self.doc_len = [len(self.tokenize(doc)) for doc in documents]
        self.avg_doc_len = sum(self.doc_len) / len(documents) if documents else 1.0
        self.doc_freqs = []
        self.idf = {}
        self._initialize()

    def tokenize(self, text: str) -> list[str]:
        # Extrae palabras clave e identificadores de código (variables, funciones)
        return re.findall(r'[a-zA-Z0-9_]+', text.lower())

    def _initialize(self):
        df = Counter()
        for doc in self.documents:
            words = set(self.tokenize(doc))
            for word in words:
                df[word] += 1
        
        N = len(self.documents)
        for word, freq in df.items():
            self.idf[word] = math.log((N - freq + 0.5) / (freq + 0.5) + 1.0)
            
        for doc in self.documents:
            self.doc_freqs.append(Counter(self.tokenize(doc)))

    def query(self, query_text: str, k: int = 3) -> list[tuple[str, dict]]:
        query_words = self.tokenize(query_text)
        scores = []
        for i in range(len(self.documents)):
            score = 0.0
            doc_len = self.doc_len[i]
            freqs = self.doc_freqs[i]
            for word in query_words:
                if word not in self.idf:
                    continue
                tf = freqs[word]
                num = tf * (self.k1 + 1)
                den = tf + self.k1 * (1.0 - self.b + self.b * (doc_len / self.avg_doc_len))
                score += self.idf[word] * (num / den)
            scores.append((score, i))
        
        scores.sort(reverse=True, key=lambda x: x[0])
        results = []
        for score, idx in scores[:k]:
            if score > 0.0:
                results.append((self.documents[idx], self.metadatas[idx]))
        return results

# ==================== RAG INGESTION ====================

def chunk_code(code: str, max_words: int = CHUNK_SIZE) -> list[str]:
    """Segmenta código por bloques de líneas."""
    lines = code.split("\n")
    chunks, current, count = [], [], 0
    for line in lines:
        words = len(line.split())
        if count + words > max_words and current:
            chunks.append("\n".join(current))
            current, count = [], 0
        current.append(line)
        count += words
    if current:
        chunks.append("\n".join(current))
    return chunks


def build_search_index() -> SimpleBM25:
    """Ingesta selectiva de código en el motor BM25."""
    all_docs, all_meta = [], []

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
                    with open(fpath, encoding="utf-8") as f:
                        code = f.read()
                except Exception:
                    continue
                for chunk in chunk_code(code):
                    all_docs.append(chunk)
                    all_meta.append({"source": fpath})

    return SimpleBM25(all_docs, all_meta)


def retrieve(index: SimpleBM25, query: str, k: int = TOP_K) -> str:
    results = index.query(query, k=k)
    if not results:
        return "(Sin contexto relevante del codebase)"
    parts = []
    for doc, meta in results:
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
    """Ejecuta un comando git robustamente, soportando encadenamientos."""
    command = command.strip()
    parts = []
    for part in command.split("&&"):
        part = part.strip()
        if part and not part.startswith("git"):
            part = f"git {part}"
        parts.append(part)
    full_command = " && ".join(parts)
    return execute_bash(full_command)


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


def should_use_rag(query: str) -> bool:
    """RAG solo se activa para queries de búsqueda/exploración de codebase."""
    trigger_words = ["buscar", "busca", "¿cómo", "explica", "¿qué", "código", "implementación",
                     "cómo se", "qué hace", "funciona", "persistencia", "estado",
                     "conexión", "api", "database", "db", "postgres", "fastapi"]
    return any(word in query.lower() for word in trigger_words)

def react_loop(query: str, index: SimpleBM25) -> str:
    """Bucle ReAct con RAG retrieval (Lazy mode)."""
    if should_use_rag(query):
        context = retrieve(index, query)
        context_block = f"---\nCONTEXTO CODEBASE\n{context}\n--- FIN CONTEXTO ---\n"
    else:
        context_block = ""

    prompt = REACT_SYSTEM.format(tools=TOOL_LIST) + f"\n{context_block}\nPregunta del usuario: {query}\n"
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
            if len(observation) > 2000:
                observation = observation[:2000] + "\n...[TRUNCATED_DUE_TO_LENGTH]..."
            messages.append({"role": "user", "content": f"Observation: {observation}"})
        else:
            messages.append({
                "role": "user",
                "content": "Observation: Formato inválido. Usa 'Action: bash' y 'Action Input: <comando>'.",
            })

    return "(Límite de pasos alcanzado sin respuesta final)"


# ==================== MAIN ====================

def main():
    print(f"[C5-REAL] ReAct Agent + BM25 RAG | Model: {MODEL_CHAT}")
    print("Ingestando codebase...")
    index = build_search_index()
    print(f"Ingestados {len(index.documents)} chunks.")
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
        answer = react_loop(query, index)
        print(f"\n{'=' * 60}")
        print(f"[FINAL]: {answer}")
        print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
