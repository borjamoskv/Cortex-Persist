#!/usr/bin/env python3
"""
ollama_connector.py

Zero-dependency local LLM connector via Ollama HTTP API.
"""

import json
import urllib.request
import urllib.error
from typing import Any, Dict, Optional

OLLAMA_HOST = "http://localhost:11434"

def generate(prompt: str, model: str = "qwen2.5-coder:7b", timeout: int = 120) -> str:
    """Send prompt to local Ollama instance and return generated text."""
    url = f"{OLLAMA_HOST}/api/generate"
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data.get("response", "")
    except (urllib.error.URLError, ConnectionError):
        return "ERROR_OLLAMA_OFFLINE"
    except Exception as e:
        return f"ERROR_OLLAMA_EXEC: {str(e)}"
