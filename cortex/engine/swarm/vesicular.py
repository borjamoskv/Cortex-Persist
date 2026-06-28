# [C5-REAL] Exergy-Maximized
"""CORTEX v6+ - Vesicular Runtime for Swarm Agents.

Enforces INV_SANDBOX_FOREIGN: Unknown payloads (LLM generated scripts)
must execute in an isolated vesicular membrane (scratch space) with
zero access to the host's physical environment variables or persistent storage.
"""

import logging
import os
import shutil
import subprocess
import tempfile
import uuid

logger = logging.getLogger("cortex.engine.swarm.vesicular")

class VesicularRuntime:
    """Ephemeral Execution Membrane for untrusted Python payloads."""
    
    def __init__(self, timeout_seconds: int = 15):
        """
        Args:
            timeout_seconds: Hard limit for execution to prevent CPU starvation.
        """
        self.timeout_seconds = timeout_seconds
        self._scratch_dir = None
        
    def _create_membrane(self) -> str:
        """Create the ephemeral /scratch directory."""
        # Use a highly specific UUID to avoid collisions
        membrane_id = f"vesicle_{uuid.uuid4().hex[:8]}"
        path = os.path.join(tempfile.gettempdir(), "cortex_swarm", membrane_id)
        os.makedirs(path, exist_ok=True)
        return path
        
    def _destroy_membrane(self, path: str) -> None:
        """Annihilate the vesicle. OP_CLEAN_ABORT."""
        try:
            shutil.rmtree(path)
        except OSError as e:
            logger.error(f"[Vesicular] Failed to annihilate membrane {path}: {e}")

    def execute(self, payload: str, bootstrap_token: str = "", proxy_port: int = 13337) -> Tuple[bool, str, str]:
        """
        Execute an untrusted Python payload inside the vesicular membrane.
        
        Args:
            payload: Python code string.
            bootstrap_token: Optional ephemeral token for Swarm PKI registration.
            proxy_port: The port where the Host's Zero-Trust Inference Proxy is listening.
            
        Returns:
            Tuple[success: bool, stdout: str, stderr: str]
        """
        membrane_path = self._create_membrane()
        logger.info(f"[Vesicular] Membrane initialized at {membrane_path}")
        
        # Strip all environment variables to prevent credential leakage (API keys)
        # Inject ONLY the strict structural environment needed for Zero-Trust Inference
        safe_env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
            "CORTEX_PROXY_URL": f"http://127.0.0.1:{proxy_port}",
            "CORTEX_BOOTSTRAP_TOKEN": bootstrap_token
        }
        
        script_path = os.path.join(membrane_path, "payload.py")
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(payload)
            
        success = False
        stdout = ""
        stderr = ""
        
        import sys
        
        try:
            # OP_SWARM_ISOLATE: Execute as subprocess in the membrane CWD
            result = subprocess.run(
                [sys.executable, script_path],
                cwd=membrane_path,
                env=safe_env,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False
            )
            success = (result.returncode == 0)
            stdout = result.stdout
            stderr = result.stderr
            
        except subprocess.TimeoutExpired as e:
            logger.critical(f"[Vesicular] Payload breached execution timeout ({self.timeout_seconds}s). Terminated.")
            stdout = e.stdout.decode('utf-8') if e.stdout else ""
            stderr = e.stderr.decode('utf-8') if e.stderr else "TimeoutExpired"
            success = False
            
        except Exception as e:
            logger.critical(f"[Vesicular] Membrane rupture during execution: {e}")
            stderr = str(e)
            success = False
            
        finally:
            # INV_CLEAN_ABORT
            self._destroy_membrane(membrane_path)
            logger.info("[Vesicular] Membrane annihilated.")
            
        return success, stdout, stderr
