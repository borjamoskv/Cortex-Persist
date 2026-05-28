import subprocess
import json
import operator
from typing import TypedDict, Annotated, Sequence, List, Dict, Any
from pathlib import Path

from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_community.chat_models import ChatOllama
from native_paths import resolve_native_binary
from context_compressor import ContextCompressor

# ◈ SCALABLE DEFAULTS
PROJECT_ROOT = Path(__file__).resolve().parent.parent
HOUND_DEBUG_BIN = PROJECT_ROOT / "engine" / "cortex-core" / "target" / "debug" / "cortex-hound"

try:
    from db import log_scaffold_experiment, get_failed_experiments
except ImportError:
    print("[!] Database layer not found. Logging locally only.")
    def log_scaffold_experiment(*args): pass
    def get_failed_experiments(*args): return []

DEFAULT_MODEL = "nemotron-3-nano:4b"
SANDBOX_PATH = "/tmp/cortex_scaffold"

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    bounty_url: str
    target_code: str
    compressed_code: str
    hypotheses: List[str]
    scaffold_commands: List[str]
    proof_of_concept: str
    is_verified: bool
    iterations: int
    metadata: Dict[str, Any]

def semantic_compressor(state: AgentState):
    """Nodo de compresión de contexto para optimizar KV-Cache."""
    meta = state.get("metadata", {})
    high_fidelity = meta.get("high_fidelity", False)
    mode_label = "HIGH-FIDELITY" if high_fidelity else "STANDARD"
    
    print(f"\n[◈ COMPRESSOR] Ejecutando Attention Matching ({mode_label})...")
    compressor = ContextCompressor()
    
    compressed = compressor.compress_code(
        state["target_code"],
        ratio=0.6,
        high_fidelity=high_fidelity
    )
    
    orig_size = len(state["target_code"])
    new_size = len(compressed)
    reduction = (1 - new_size / orig_size) * 100
    
    print(f"[◈ COMPRESSOR] Reducción: {reduction:.1f}% ({orig_size} -> {new_size} bytes) [{mode_label}]")
    
    return {
        "compressed_code": compressed,
        "metadata": {**meta, "original_code_size": orig_size, "compression_ratio": 0.6, "high_fidelity": high_fidelity}
    }

def mythos_analyzer(state: AgentState):
    print(f"\n[◈ MYTHOS] Analizando {state['bounty_url']}...")
    
    # Use compressed code for inference to save KV-cache
    target = state.get("compressed_code", state["target_code"])
    
    model_name = state.get("metadata", {}).get("routed_model", DEFAULT_MODEL)
    print(f"\n[◈ MYTHOS] Enrutando inferencia a endpoint local OLLAMA ({model_name})...")
    llm = ChatOllama(model=model_name, base_url="http://localhost:11434", temperature=0)
    
    prompt = (f"Target Code (Compressed):\n{target}\n\nInstructions:\n"
              "1. THINK SURGICAL: Identify exactly 3 logic flaws with zero noise. Focus on high-exergy vulnerabilities.\n"
              "2. THINK SIMPLE: Provide MINIMAL shell commands for STRIKE. No unnecessary dependencies.\n"
              "3. GOAL-DRIVEN: Verify each hook targets the $1M Firedancer bounty invariants.\n"
              "4. Output MUST be valid JSON: {\"hypotheses\": [...], \"commands\": [...]}")
    try:
        resp = llm.invoke([HumanMessage(content=prompt)])
        data = json.loads(resp.content.strip().split("```json")[-1].split("```")[0].strip())
        return {"hypotheses": data.get("hypotheses", []), "scaffold_commands": data.get("commands", []), "iterations": state.get("iterations", 0) + 1}
    except Exception as e:
        return {"hypotheses": [f"FAIL: {e}"], "scaffold_commands": ["exit 1"], "iterations": state.get("iterations", 0) + 1}

def formal_verification(state: AgentState):
    print(f"[◈ FORMAL] Native Scan...")
    tmp_file = Path("/tmp/target_mythos.sol")
    tmp_file.write_text(state["target_code"]) # Use original for formal verification
    rust_bin = resolve_native_binary("cortex-hound", "CORTEX_NATIVE_HOUND_BIN")
    if rust_bin is None and HOUND_DEBUG_BIN.is_file(): rust_bin = HOUND_DEBUG_BIN
    if rust_bin:
        res = subprocess.run([str(rust_bin), "static", str(tmp_file)], capture_output=True, text=True)
        if "REENTRANCY DETECTED" in res.stdout:
            return {"is_verified": False, "proof_of_concept": "REENTRANCY_FOUND"}
    return {"is_verified": True}

def glasswing_scaffold(state: AgentState):
    print(f"[◈ SCAFFOLD] Native Scaffold...")
    rust_bin = resolve_native_binary("cortex-hound", "CORTEX_NATIVE_HOUND_BIN")
    if rust_bin is None and HOUND_DEBUG_BIN.is_file(): rust_bin = HOUND_DEBUG_BIN
    cmd_json = json.dumps({"commands": state["scaffold_commands"]})
    if rust_bin:
        res = subprocess.run([str(rust_bin), "scaffold", cmd_json], capture_output=True, text=True)
        try:
            verdict = json.loads(res.stdout.strip())
            return {"proof_of_concept": res.stdout, "is_verified": verdict.get("verdict") == "C5-REAL"}
        except: pass
    return {"is_verified": False, "proof_of_concept": "SCAFFOLD_FAIL"}

def verifier_logic(state: AgentState):
    log_scaffold_experiment(state["bounty_url"], "\n".join(state["hypotheses"]), state["scaffold_commands"], state.get("proof_of_concept", ""), state.get("is_verified", False))
    return {"is_verified": state.get("is_verified", False)}

def build_mythos_graph():
    builder = StateGraph(AgentState)
    builder.add_node("compressor", semantic_compressor)
    builder.add_node("analyzer", mythos_analyzer)
    builder.add_node("formal", formal_verification)
    builder.add_node("scaffold", glasswing_scaffold)
    builder.add_node("verifier", verifier_logic)
    
    builder.set_entry_point("compressor")
    builder.add_edge("compressor", "analyzer")
    builder.add_edge("analyzer", "formal")
    builder.add_conditional_edges("formal", lambda s: "scaffold" if s["is_verified"] else "verifier")
    builder.add_edge("scaffold", "verifier")
    builder.add_conditional_edges("verifier", lambda s: "finalize" if s["is_verified"] or s["iterations"] >= 3 else "analyzer", {"finalize": END, "analyzer": "analyzer"})
    return builder.compile()

if __name__ == "__main__":
    engine = build_mythos_graph()
    print("◈ HOUND-Ω READY (Semantic Compression Active)")
