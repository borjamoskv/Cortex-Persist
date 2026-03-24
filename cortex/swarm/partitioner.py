import logging
import re
from enum import Enum

logger = logging.getLogger("cortex.swarm.partitioner")

class SwarmEnclave(Enum):
    PRIVATE = "private"     # Local processing only
    VECTOR = "vector"       # Knowledge / Search based
    EXECUTION = "execution" # Tool using / Action based
    GOVERNANCE = "governance" # Multi-swarm audit / Policy

class SwarmPartitioner:
    """
    Ω-Partitioner: Recursive Universe Slicing.
    Categorizes tasks and delegates to the appropriate specialized sub-swarm Enclave.
    """

    @staticmethod
    async def partition_task(task_description: str) -> SwarmEnclave:
        """Analyze task text using regex patterns to determine the optimal Enclave."""
        desc = task_description.lower()
        
        # Prioritized patterns for higher accuracy
        patterns = {
            SwarmEnclave.EXECUTION: [
                r"\b(write|create|deploy|fix|run|execute|forge|build|generate|implement|develop|configure|setup|install|perform|action|tool|use tool)\b",
                r"code|script|program|api call|database operation",
            ],
            SwarmEnclave.VECTOR: [
                r"\b(search|find|research|lookup|query|moltbook|retrieve|get information|data|knowledge|fact|explain|summarize|analyze)\b",
                r"report|document|article|webpage|database|vector store",
            ],
            SwarmEnclave.PRIVATE: [
                r"\b(secret|private|personal|encrypt|vault|auth|authenticate|authorize|secure|confidential|sensitive|my data)\b",
                r"credentials|password|token|identity|privacy",
            ],
        }
        
        # Check for specific patterns first
        for enclave, regex_list in patterns.items():
            if any(re.search(p, desc) for p in regex_list):
                return enclave
        
        # If no specific pattern matches, default to GOVERNANCE
        # GOVERNANCE can also be explicitly triggered by certain keywords if needed
        if re.search(r"\b(audit|policy|review|oversight|compliance|monitor|govern)\b", desc):
            return SwarmEnclave.GOVERNANCE
            
        return SwarmEnclave.GOVERNANCE

    @staticmethod
    async def shard_complex_task(complex_task: str) -> dict[SwarmEnclave, list[str]]:
        """Splits a complex multi-hop task into atomic sub-tasks by Enclave."""
        # Simplified recursive split for Level 200 prototype
        shards: dict[SwarmEnclave, list[str]] = {e: [] for e in SwarmEnclave}
        
        # Mock splitting logic: Assume task segments separated by ';' or 'then'
        segments = complex_task.replace("then", ";").split(";")
        for seg in segments:
            seg = seg.strip()
            if not seg:
                continue
            enclave = await SwarmPartitioner.partition_task(seg)
            shards[enclave].append(seg)
            
        logger.info("SwarmPartitioner: Sharded complex task into %d enclaves.", len([s for s in shards.values() if s]))
        return shards
