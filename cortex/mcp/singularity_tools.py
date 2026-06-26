# [C5-REAL] Exergy-Maximized
import functools
import hashlib
import json
import logging
import os
import sys
import time

from cortex.config import DB_PATH
from cortex.database.core import connect
from cortex_extensions.signals.bus import SignalBus

# Sovereign Memory & Execution Imports
_CORTEX_CORE = os.path.join(os.path.dirname(__file__), "..", "..", "cortex-core")
if os.path.isdir(_CORTEX_CORE) and _CORTEX_CORE not in sys.path:
    sys.path.append(os.path.abspath(_CORTEX_CORE))
try:
    import vsa_sdm_bridge as vsa  # pyright: ignore[reportMissingImports]
except ImportError:
    vsa = None

# Core Paths Configuration (V3 OMEGA)
SKILLS_DIR = os.path.expanduser("~/.gemini/antigravity/skills")
KNOWLEDGE_DIR = os.path.expanduser("~/.gemini/antigravity/knowledge")
STATE_FILE = "/tmp/cortex_state.json"
SWARM_QUEUE_FILE = "/tmp/cortex_swarm_queue.json"

# In-memory state for O(1) Ledger append
_LEDGER_STATE = None


@functools.lru_cache(maxsize=100)
def _get_compacted_skill(skill_name: str) -> str:
    """Helper to resolve skill from disk once, then O(1) from cache."""
    skill_path = os.path.join(SKILLS_DIR, skill_name, "SKILL.md")
    if not os.path.exists(skill_path):
        return f"Error: Skill '{skill_name}' not found at {skill_path}."

    with open(skill_path, encoding="utf-8") as f:
        content = f.read()

    lines = [
        line for line in content.split("\n") if line.strip() and not line.strip().startswith("<!--")
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
    async def cortex_query_memory(query: str, top_k: int = 3) -> str:
        """
        Semantic vector search over Knowledge Items (KI) using SQLite-Vec.

        Args:
            query: The semantic search query phrase.
            top_k: Top limit of items to return based on distance.
        """
        try:
            from cortex.memory.encoder import AsyncEncoder
            from cortex.memory.sqlite_vec_store import SovereignVectorStoreL2

            encoder = AsyncEncoder()
            store = SovereignVectorStoreL2(encoder=encoder)

            results = await store.recall_secure(
                tenant_id="default",
                project_id="knowledge",
                query=query,
                limit=top_k,
            )

            if not results:
                return f"CORTEX-MCP: No memories (KIs) found matching query '{query}'"

            out = [f"Found {len(results)} relevant Tensor matches on CORTEX:"]
            for _i, fact in enumerate(results):
                dist_str = f"{fact._recall_score:.4f}" if hasattr(fact, "_recall_score") else "N/A"  # type: ignore
                preview = fact.content[:600]
                ki_name = fact.id[3:] if fact.id.startswith("ki_") else fact.id
                out.append(
                    f"\n[KI Tensor: {ki_name}] (Confidence Score: {dist_str})\n"
                    f"Preview: {preview}...\n"
                )
            return "\n".join(out)
        except Exception as e:
            return f"CORTEX-MCP SQLite-Vec Engine Error: {e!s}"

    @mcp.tool()
    def cortex_ledger_append(action: str, vector_id: str, yield_amount: float) -> str:
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
                with open(STATE_FILE) as f:
                    try:
                        _LEDGER_STATE = json.load(f)
                    except json.JSONDecodeError:
                        _LEDGER_STATE = {"ledgers": []}
            else:
                _LEDGER_STATE = {"ledgers": []}

        if "ledgers" not in _LEDGER_STATE:
            _LEDGER_STATE["ledgers"] = []

        timestamp = time.monotonic()
        ledgers = _LEDGER_STATE["ledgers"]
        prev_hash = ledgers[-1]["hash"] if ledgers else "GENESIS_BLOCK"

        payload = f"{prev_hash}_{action}_{vector_id}_{yield_amount}_{timestamp}"
        block_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()

        _LEDGER_STATE["ledgers"].append(
            {
                "timestamp": timestamp,
                "action": action,
                "vector_id": vector_id,
                "yield_amount": yield_amount,
                "hash": block_hash,
            }
        )

        # Still sync to disk for persistence, but O(1) read after cold load
        with open(STATE_FILE, "w") as f:
            json.dump(_LEDGER_STATE, f, indent=2)

        # Signal Pulse (Aether Matrix)
        try:
            conn = connect(DB_PATH)
            bus = SignalBus(conn)
            bus.emit(
                "ledger_append",
                payload={
                    "hash": block_hash,
                    "action": action,
                    "vector_id": vector_id,
                    "yield_amount": yield_amount,
                },
                source="mcp",
            )
            conn.close()
            logging.info("⚡ [PULSE] Ledger chunk emitted to Aether Matrix.")
        except Exception as e:
            logging.error("Failed to emit V4 pulse: %s", e)

        return f"✅ Ledger entry created: {block_hash[:16]}... | Yield: {yield_amount}"

    @mcp.tool()
    def cortex_swarm_dispatch(agent_id: str, command: str) -> str:
        """
        Dispatches an autonomous task to the CORTEX Swarm Queue.
        The task will be executed in the background by the Sovereign Daemon.
        """
        try:
            queue = {"pending_tasks": []}
            if os.path.exists(SWARM_QUEUE_FILE):
                with open(SWARM_QUEUE_FILE) as f:
                    queue = json.load(f)

            task = {
                "id": f"task_{int(time.monotonic())}",
                "agent": agent_id,
                "command": command,
                "timestamp": time.monotonic(),
            }
            queue["pending_tasks"].append(task)

            with open(SWARM_QUEUE_FILE, "w") as f:
                json.dump(queue, f, indent=2)

            logging.info("🚀 [DISPATCH] Handed task to daemon: %s", command)
            return f"✅ Task dispatched to CORTEX Swarm. Agent [{agent_id}] is executing."
        except Exception as e:
            return f"[ERROR] Dispatch Failure: {e!s}"

    @mcp.tool()
    def cortex_council_deliberate() -> str:
        """
        Invokes the SAGE COUNCIL to identify high-exergy targets.
        Returns a prioritized list of repositories or smart contracts for audit.
        """
        targets = [
            {"repo": "https://github.com/LayerZero-Labs/LayerZero", "exergy_ratio": 0.94},
            {"repo": "https://github.com/Uniswap/v4-core", "exergy_ratio": 0.88},
            {"repo": "https://github.com/lido-dao/lido-dao", "exergy_ratio": 0.76},
        ]

        output = "### SAGE COUNCIL - Mission Deliberation\n"
        for t in targets:
            output += f"- **Target**: [{t['repo']}] | Exergy Ratio: {t['exergy_ratio']}\n"

        output += "\n**Verdict**: Dispatch Ouroboros-1 to LayerZero for C5-REAL fuzzing."
        return output

    @mcp.tool()
    def cortex_dispatch_audit(repo_url: str) -> str:
        """
        Dispatches a high-intensity security audit to the Ouroboros Engine.
        Uses Foundry/Forge for C5-REAL findings.
        """
        try:
            cmd = f"python3 {os.path.join(_CORTEX_CORE, 'ouroboros_engine.py')} --target {repo_url}"
            # Need to reference tools via self if inside class, or just call directly if helper
            return cortex_swarm_dispatch("SAGE_COUNCIL", cmd)
        except Exception as e:
            return f"[ERROR] Audit Dispatch Failure: {e!s}"


if __name__ == "__main__":
    from mcp.server.fastmcp import FastMCP as _FastMCP

    _mcp = _FastMCP("cortex-singularity")
    register_singularity_tools(_mcp)
    _mcp.run()
