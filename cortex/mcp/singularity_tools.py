import functools
import sqlite3
from cortex.config import DB_PATH
from cortex.extensions.signals.bus import SignalBus

try:
    import chromadb
except ImportError:
    chromadb = None

# Core Paths Configuration (V3 OMEGA)
SKILLS_DIR = os.path.expanduser("~/.gemini/antigravity/skills")
KNOWLEDGE_DIR = os.path.expanduser("~/.gemini/antigravity/knowledge")
STATE_FILE = "/tmp/cortex_state.json"
SWARM_QUEUE_FILE = "/tmp/cortex_swarm_queue.json"
CHROMA_DB_PATH = os.path.expanduser("~/.cortex/chroma_db")

# In-memory state for O(1) Ledger append
_LEDGER_STATE = None


@functools.lru_cache(maxsize=100)
def _get_compacted_skill(skill_name: str) -> str:
    """Helper to resolve skill from disk once, then O(1) from cache."""
    skill_path = os.path.join(SKILLS_DIR, skill_name, "SKILL.md")
    if not os.path.exists(skill_path):
        return f"Error: Skill '{skill_name}' not found at {skill_path}."

    with open(skill_path, "r", encoding="utf-8") as f:
        content = f.read()

    lines = [
        line for line in content.split("\n")
        if line.strip() and not line.strip().startswith("<!--")
    ]
    return "\n".join(lines)


def register_singularity_tools(mcp) -> None:
    """Register v3 singularity capabilities (skills, memory, ledger, swarm)."""

    @mcp.tool()
    def cortex_execute_skill(skill_name: str, task_context: str) -> str:
        """
        Executes a Sovereign Skill by retrieving core instructions and
        preparing it for agent execution via Shannon Compaction.

        Args:
            skill_name: The folder name of the target skill.
            task_context: Input specifies dynamic parameters of the execution.
        """
        compacted_content = _get_compacted_skill(skill_name)
        if compacted_content.startswith("Error:"):
            return compacted_content

        directive = (
            "You are operating within the MOSKV-1 environment. "
            "Execute the task immediately according to the strict "
            "skill instructions mapped above."
        )

        return (
            f"--- SKILL INSTRUCTIONS ({skill_name}) ---\n"
            f"{compacted_content}\n\n"
            f"--- TASK CONTEXT ---\n"
            f"{task_context}\n\n"
            f"--- DIRECTIVE ---\n"
            f"{directive}"
        )

    @mcp.tool()
    def cortex_query_memory(query: str, top_k: int = 3) -> str:
        """
        Semantic vector search over Knowledge Items (KI) using ChromaDB.

        Args:
            query: The semantic search query phrase.
            top_k: Top limit of items to return based on distance.
        """
        if not chromadb:
            return "CORTEX-MCP: ChromaDB is missing. Run `uv add chromadb`."
        try:
            client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
            collection = client.get_collection("cortex_knowledge_base")
            res = collection.query(query_texts=[query], n_results=top_k)

            ids = res['ids'][0] if res['ids'] else []
            docs = res['documents'][0] if res['documents'] else []
            dists = res['distances'][0] if 'distances' in res else []

            if not ids:
                return (
                    f"CORTEX-MCP: No memories (KIs) found matching "
                    f"query '{query}'"
                )

            out = [f"Found {len(ids)} relevant Tensor matches on CORTEX:"]
            for i, doc_id in enumerate(ids):
                dist_str = f"{dists[i]:.4f}" if i < len(dists) else "N/A"
                preview = docs[i][:600]
                out.append(
                    f"\n[KI Tensor: {doc_id}] (Cosine Distance: {dist_str})\n"
                    f"Preview: {preview}...\n"
                )
            return "\n".join(out)
        except Exception as e:
            return f"CORTEX-MCP ChromaDB Engine Error: {str(e)}"

    @mcp.tool()
    def cortex_ledger_append(
        action: str, vector_id: str, yield_amount: float
    ) -> str:
        """
        Cryptographic write to the CORTEX-Persist ledger. Secures Exergy via
        SHA-256 Merkle chain.

        Args:
            action: Standard action name.
            vector_id: Execution target identifier (bounty, code hunt, etc).
            yield_amount: Generated value or exergy unit delta (numeric float).
        """
        global _LEDGER_STATE
        if _LEDGER_STATE is None:
            if os.path.exists(STATE_FILE):
                with open(STATE_FILE, "r") as f:
                    try:
                        _LEDGER_STATE = json.load(f)
                    except json.JSONDecodeError:
                        _LEDGER_STATE = {"ledgers": []}
            else:
                _LEDGER_STATE = {"ledgers": []}

        if "ledgers" not in _LEDGER_STATE:
            _LEDGER_STATE["ledgers"] = []

        timestamp = time.time()
        ledgers = _LEDGER_STATE["ledgers"]
        prev_hash = ledgers[-1]["hash"] if ledgers else "GENESIS_BLOCK"

        payload = f"{prev_hash}_{action}_{vector_id}_{yield_amount}_{timestamp}"
        block_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()

        _LEDGER_STATE["ledgers"].append({
            "timestamp": timestamp,
            "action": action,
            "vector_id": vector_id,
            "yield_amount": yield_amount,
            "hash": block_hash
        })

        # Still sync to disk for persistence, but O(1) read after cold load
        with open(STATE_FILE, "w") as f:
            json.dump(_LEDGER_STATE, f, indent=2)

        # Signal Pulse (Aether Matrix)
        try:
            conn = sqlite3.connect(DB_PATH)
            bus = SignalBus(conn)
            bus.emit("ledger_append", payload={
                "hash": block_hash,
                "action": action,
                "vector_id": vector_id,
                "yield_amount": yield_amount
            })
            conn.close()
        except Exception:
            pass

        msg = (
            f"CORTEX-MCP: Ledger written successfully to C5-REAL: "
            f"+{yield_amount} YIELD appended to [{vector_id}]. "
            f"Cryptogram: {block_hash[:16]}..."
        )
        return msg

    @mcp.tool()
    def cortex_swarm_dispatch(agent_type: str, payload_json: str) -> str:
        """
        Spawns a sub-task into the swarm execution queue.

        Args:
            agent_type: Specific target sub-agent to invoke queue for.
            payload_json: Encoded JSON object for parameters.
        """
        if not os.path.exists(SWARM_QUEUE_FILE):
            with open(SWARM_QUEUE_FILE, "w") as f:
                json.dump({"pending_tasks": []}, f)

        with open(SWARM_QUEUE_FILE, "r") as f:
            try:
                queue = json.load(f)
            except json.JSONDecodeError:
                queue = {"pending_tasks": []}

        if "pending_tasks" not in queue:
            queue["pending_tasks"] = []

        try:
            parsed_payload = json.loads(payload_json)
        except json.JSONDecodeError:
            return (
                "CORTEX-MCP Error: The payload_json is not a valid "
                "JSON structure."
            )

        task_entry = {
            "agent": agent_type,
            "payload": parsed_payload
        }
        queue["pending_tasks"].append(task_entry)

        with open(SWARM_QUEUE_FILE, "w") as f:
            json.dump(queue, f, indent=2)

        # Signal Pulse (Aether Matrix)
        try:
            conn = sqlite3.connect(DB_PATH)
            bus = SignalBus(conn)
            bus.emit("swarm_task", payload={
                "agent": agent_type,
                "payload": parsed_payload
            })
            conn.close()
        except Exception:
            pass

        return (
            f"CORTEX-MCP: Swarm Task #{len(queue['pending_tasks'])} "
            f"dispatched successfully for {agent_type}."
        )

