# [C5-REAL] Exergy-Maximized
import json
import logging
import urllib.error
import urllib.request
from typing import Optional

logger = logging.getLogger("cortex.llm.raw_client")

class RawLLMClient:
    """
    C5-REAL Zero-Entropy LLM Client.
    Direct HTTP communication via urllib to bypass LangChain bloat.
    """
    def __init__(self, base_url: str = "http://localhost:11434/api", model: str = "qwen2.5-coder:32b"):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def generate(self, prompt: str, system: Optional[str] = None, temperature: float = 0.0) -> str:
        """Synchronous completion via Ollama."""
        url = f"{self.base_url}/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature}
        }
        if system:
            payload["system"] = system

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode("utf-8"))
                return result.get("response", "")
        except urllib.error.URLError as e:
            logger.error(f"[RawLLM] Error calling Ollama: {e}")
            raise RuntimeError(f"Ollama API error: {e}")

    def chat(self, messages: list[dict[str, str]], temperature: float = 0.0) -> str:
        """Synchronous chat completion via Ollama."""
        url = f"{self.base_url}/chat"
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature}
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        
        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                result = json.loads(response.read().decode("utf-8"))
                return result.get("message", {}).get("content", "")
        except urllib.error.URLError as e:
            logger.error(f"[RawLLM] Error in chat endpoint: {e}")
            raise RuntimeError(f"Ollama Chat error: {e}")
