# [C5-REAL] Exergy-Maximized
"""CORTEX v6+ - Zero-Trust Inference Proxy.

Host-side proxy that isolates the GEMINI_API_KEY from the Vesicular Runtime.
Agents must sign their LLM requests. The Proxy verifies their identity
against the TrustMatrix before forwarding the request to the frontier model.
"""

from babylon60.crypto.hash_registry import cortex_hash_raw
import base64
import logging
import os
import threading
from typing import Optional

from pydantic import BaseModel

try:
    import uvicorn
    from fastapi import FastAPI, HTTPException
except ImportError:
    pass

from cortex.consensus.pki import trust_matrix
from cortex.extensions.llm.client import SovereignLLMClient  # Assume this is the real client

logger = logging.getLogger("cortex.swarm.inference_proxy")

app = FastAPI(title="CORTEX Zero-Trust Inference Proxy")


class InferenceRequest(BaseModel):
    agent_id: str
    prompt: str
    signature_b64: str  # Signature of sha256(prompt)


@app.post("/v1/inference")
async def proxy_inference(req: InferenceRequest):
    """
    Validates the agent's signature and proxies the inference request.
    """
    # 1. Look up agent in TrustMatrix
    public_key = trust_matrix.get_peer_key(req.agent_id)
    if not public_key:
        logger.critical(f"[InferenceProxy] REJECTED. Unknown or revoked agent: {req.agent_id}")
        raise HTTPException(status_code=403, detail="Agent Identity Not Found or Revoked")

    # 2. Verify Signature
    try:
        sig_bytes = base64.b64decode(req.signature_b64)
        prompt_hash = cortex_hash_raw(req.prompt.encode("utf-8"))
        public_key.verify(sig_bytes, prompt_hash)
    except Exception as e:
        logger.critical(
            f"[InferenceProxy] REJECTED. Invalid cryptographic signature from {req.agent_id}: {e}"
        )
        raise HTTPException(status_code=403, detail="Invalid Signature")

    # 3. Execution (Host has the GEMINI_API_KEY)
    logger.info(f"[InferenceProxy] Authorized inference request from {req.agent_id}. Proxying...")

    # We instantiate the client here so it picks up the Host's env vars
    try:
        # Fallback to a mock response if we are in testing
        if os.environ.get("CORTEX_TESTING"):
            return {"response": f"MOCK_RESPONSE_FOR_{req.agent_id}"}

        client = SovereignLLMClient()
        response = client.generate(req.prompt)  # type: ignore[call-arg]
        return {"response": response}
    except Exception as e:
        logger.error(f"[InferenceProxy] Upstream LLM failure: {e}")
        raise HTTPException(status_code=502, detail="Upstream Inference Failed")


class InferenceProxyDaemon:
    """Daemon to run the proxy in a background thread."""

    def __init__(self, port: int = 13337):
        self.port = port
        self._thread: Optional[threading.Thread] = None
        self._server: Optional[uvicorn.Server] = None

    def start(self):
        config = uvicorn.Config(app, host="127.0.0.1", port=self.port, log_level="warning")
        self._server = uvicorn.Server(config)
        self._thread = threading.Thread(target=self._server.run, daemon=True)
        self._thread.start()
        logger.info(f"[InferenceProxy] Started Zero-Trust Proxy on 127.0.0.1:{self.port}")

    def stop(self):
        if self._server:
            self._server.should_exit = True
        if self._thread:
            self._thread.join(timeout=2.0)
        logger.info("[InferenceProxy] Stopped Zero-Trust Proxy.")


# Global Proxy Daemon
inference_proxy = InferenceProxyDaemon()
