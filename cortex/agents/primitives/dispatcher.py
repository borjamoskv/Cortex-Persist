import logging
import math
import os
import subprocess
import sys
from collections.abc import Callable
from types import MappingProxyType
from typing import Any

from cortex.agents.primitives.registry import apex_registry

logger = logging.getLogger(__name__)

class ApexDispatcher:
    """
    C5-REAL: Execution Engine for MOSKV-1 APEX Primitives.
    Translates structural invariants and semantic APEX intents into 
    physical state mutations (Disk, Git, Memory).
    """
    def __init__(self) -> None:
        self._handlers: dict[str, Callable[..., Any]] = {}
        self._register_native_handlers()

    def _register_native_handlers(self) -> None:
        """Binds OP_ names to physical Python execution methods."""
        # Core & Security
        self._bind("OP_GIT_SENTINEL", self._op_git_sentinel)
        self._bind("OP_APOPTOSIS", self._op_apoptosis)
        self._bind("OP_ANNIHILATE", self._op_annihilate)
        self._bind("OP_OOM_SIM", self._op_oom_sim)
        self._bind("OP_HALT_LOOP", self._op_halt_loop)
        
        # Crypto & Data
        self._bind("OP_B58_ENCODE", self._op_b58_encode)
        self._bind("OP_B58_DECODE", self._op_b58_decode)
        self._bind("OP_SHRED_KEY", self._op_shred_key)
        
        # Memory & Thermodynamics
        self._bind("OP_FREEZE_MEM", self._op_freeze_mem)
        self._bind("OP_MEASURE_SHANNON", self._op_measure_shannon)

    def _bind(self, op_name: str, handler: Callable[..., Any]) -> None:
        prim = next((p for p in apex_registry.list_primitives() if p.name == op_name), None)
        if prim:
            self._handlers[prim.id] = handler

    def execute(self, op_name: str, **kwargs: Any) -> Any:
        """Find primitive by name (e.g. OP_GIT_SENTINEL) and execute its deterministic bound handler."""
        prim = next((p for p in apex_registry.list_primitives() if p.name == op_name), None)
        if not prim:
            raise ValueError(f"[C5-REAL] FATAL: Primitive {op_name} not found in APEX_REGISTRY.")
            
        handler = self._handlers.get(prim.id)
        if not handler:
            raise NotImplementedError(f"[C5-REAL] ERROR: Physical handler for {op_name} ({prim.id}) is not yet wired.")
            
        logger.info(f"[APEX DISPATCH] Executing {op_name}...")
        return handler(**kwargs)

    # --- PHYSICAL IMPLEMENTATIONS (C5-REAL) ---
    
    def _op_git_sentinel(self, commit_msg: str, force: bool = False, path: str = ".") -> str:
        """OP_GIT_SENTINEL: Causal persistence via cryptographic commit."""
        add_cmd = ["git", "add"]
        if force:
            add_cmd.append("-f")
        add_cmd.append(path)
            
        try:
            subprocess.run(add_cmd, check=True, capture_output=True, timeout=10)
            res = subprocess.run(["git", "commit", "--no-gpg-sign", "-m", commit_msg], capture_output=True, text=True, timeout=15)
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(f"[C5-REAL] FATAL: Git Sentinel hung and timed out. Possible lock or tty issue. Cmd: {e.cmd}")
        
        if res.returncode != 0 and "nothing to commit" not in res.stdout and "working tree clean" not in res.stdout:
            raise RuntimeError(f"Git Sentinel failed: {res.stderr}")
            
        try:
            log_res = subprocess.run(["git", "log", "-1", "--format=%H"], capture_output=True, text=True, timeout=5)
            return log_res.stdout.strip()
        except subprocess.TimeoutExpired:
            return "UNKNOWN_HASH_TIMEOUT"

    def _op_apoptosis(self) -> None:
        """OP_APOPTOSIS: Intentional context termination due to extreme entropy."""
        logger.critical("[C5-REAL] Entropy threshold exceeded. Initiating Apoptosis (SIGKILL).")
        sys.exit(1)

    def _op_oom_sim(self) -> None:
        """OP_OOM_SIM: Simulate Out-Of-Memory to escape logic paradoxes."""
        logger.critical("[C5-REAL] Simulating OOM to bypass logic lock.")
        raise MemoryError("[APEX] Simulated OOM")

    def _op_halt_loop(self) -> None:
        """OP_HALT_LOOP: Breaks an infinite generative or LLM loop forcefully."""
        logger.warning("[C5-REAL] Anti-Limerence Kill Criteria invoked. Halting generative loop.")
        raise StopIteration("[APEX] Generative loop halted.")

    def _op_annihilate(self, target_path: str) -> None:
        """OP_ANNIHILATE: Authorized rm -rf."""
        if not target_path.startswith("/"):
            raise ValueError("[C5-REAL] P0 VIOLATION (INV_ABSOLUTE_PATH): Annihilate requires absolute paths.")
        if target_path in ("/", "/private/var/db", "/System"):
            raise ValueError("[C5-REAL] P0 VIOLATION (INV_SYSTEM_ROOT): Cannot annihilate protected zones.")
            
        subprocess.run(["rm", "-rf", target_path], check=True)
        logger.warning(f"[APEX] Annihilated {target_path}")

    def _op_b58_encode(self, payload: bytes) -> str:
        """OP_B58_ENCODE: Base58 encoding for shorter tamper-evident hashes."""
        import base58
        return base58.b58encode(payload).decode('utf-8')

    def _op_b58_decode(self, payload: str) -> bytes:
        """OP_B58_DECODE: Base58 decode back to original entropy."""
        import base58
        return base58.b58decode(payload)

    def _op_shred_key(self, key_bytes: bytearray) -> None:
        """OP_SHRED_KEY: Cryptographically shred ephemeral key material."""
        if not isinstance(key_bytes, bytearray):
            raise TypeError("[C5-REAL] Shredding requires mutable bytearray.")
        # Overwrite with pseudo-random bytes
        for i in range(len(key_bytes)):
            key_bytes[i] = os.urandom(1)[0]
        logger.info("[APEX] Ephemeral key material shredded.")

    def _op_freeze_mem(self, state: dict[Any, Any]) -> MappingProxyType[Any, Any]:
        """OP_FREEZE_MEM: Convert a mutable dictionary into a read-only MappingProxyType."""
        return MappingProxyType(state)

    def _op_measure_shannon(self, data: str) -> float:
        """OP_MEASURE_SHANNON: Calculate the Shannon entropy of a string."""
        if not data:
            return 0.0
        entropy = 0.0
        length = len(data)
        freqs = {char: data.count(char) for char in set(data)}
        for count in freqs.values():
            p = count / length
            entropy -= p * math.log2(p)
        return entropy

apex_dispatcher = ApexDispatcher()
