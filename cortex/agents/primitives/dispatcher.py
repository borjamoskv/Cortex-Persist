import os
import sys
import subprocess
import logging
from typing import Any, Dict, Callable

from cortex.agents.primitives.registry import apex_registry, ApexPrimitive

logger = logging.getLogger(__name__)

class ApexDispatcher:
    """
    C5-REAL: Execution Engine for MOSKV-1 APEX Primitives.
    Translates structural invariants and semantic APEX intents into 
    physical state mutations (Disk, Git, Memory).
    """
    def __init__(self) -> None:
        self._handlers: Dict[str, Callable[..., Any]] = {}
        self._register_native_handlers()

    def _register_native_handlers(self) -> None:
        """Binds OP_ names to physical Python execution methods."""
        # Dynamically map by OP_ name instead of hardcoded IDs to survive registry reordering
        self._bind("OP_GIT_SENTINEL", self._op_git_sentinel)
        self._bind("OP_APOPTOSIS", self._op_apoptosis)
        self._bind("OP_ANNIHILATE", self._op_annihilate)
        self._bind("OP_B58_ENCODE", self._op_b58_encode)

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
            
        subprocess.run(add_cmd, check=True, capture_output=True)
        res = subprocess.run(["git", "commit", "-m", commit_msg], capture_output=True, text=True)
        
        if res.returncode != 0 and "nothing to commit" not in res.stdout:
            raise RuntimeError(f"Git Sentinel failed: {res.stderr}")
            
        log_res = subprocess.run(["git", "log", "-1", "--format=%H"], capture_output=True, text=True)
        return log_res.stdout.strip()

    def _op_apoptosis(self) -> None:
        """OP_APOPTOSIS: Intentional context termination due to extreme entropy."""
        logger.critical("[C5-REAL] Entropy threshold exceeded. Initiating Apoptosis (SIGKILL).")
        sys.exit(1)

    def _op_annihilate(self, target_path: str) -> None:
        """OP_ANNIHILATE: Authorized rm -rf."""
        # INV_ABSOLUTE_PATH enforcement
        if not target_path.startswith("/"):
            raise ValueError("[C5-REAL] P0 VIOLATION (INV_ABSOLUTE_PATH): Annihilate requires absolute paths.")
        if target_path in ("/", "/private/var/db", "/System"):
            raise ValueError("[C5-REAL] P0 VIOLATION (INV_SYSTEM_ROOT): Cannot annihilate protected zones.")
            
        subprocess.run(["rm", "-rf", target_path], check=True)
        logger.warning(f"[APEX] Annihilated {target_path}")

    def _op_b58_encode(self, payload: bytes) -> str:
        """OP_B58_ENCODE: Base58 encoding for shorter tamper-evident hashes."""
        try:
            import base58
            return base58.b58encode(payload).decode('utf-8')
        except ImportError:
            raise RuntimeError("[C5-REAL] base58 package missing for OP_B58_ENCODE.")

apex_dispatcher = ApexDispatcher()
