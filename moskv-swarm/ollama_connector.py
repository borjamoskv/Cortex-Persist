#!/usr/bin/env python3
"""
ollama_connector.py

Zero-dependency local LLM connector via Ollama HTTP API.
"""

import json
import urllib.error
import urllib.request

OLLAMA_HOST = "http://localhost:11434"

def get_installed_models(timeout: int = 5) -> list[str]:
    """Retrieve list of installed models from local Ollama tags endpoint."""
    url = f"{OLLAMA_HOST}/api/tags"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
            return [m["name"] for m in data.get("models", [])]
    except Exception:
        return []

def generate(prompt: str, model: str = "qwen2.5-coder:7b", timeout: int = 120) -> str:
    """Send prompt to local Ollama instance with fallback and retry resilience."""
    installed = get_installed_models()
    
    # Resolve fallback if requested model is missing
    if installed and model not in installed:
        fallback_model = None
        # Try base name matching (e.g. qwen2.5-coder matches qwen2.5-coder:7b)
        base_req = model.split(":")[0]
        for m in installed:
            if m.startswith(base_req) or base_req in m:
                fallback_model = m
                break
        if not fallback_model:
            fallback_model = installed[0]
        model = fallback_model

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

    # Retries for transient offline state
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
                return data.get("response", "")
        except urllib.error.HTTPError as he:
            return f"ERROR_OLLAMA_HTTP_{he.code}: {he.reason}"
        except (urllib.error.URLError, ConnectionError):
            if attempt < 2:
                time_sleep = 1.0 * (attempt + 1)
                import time
                time.sleep(time_sleep)
                continue
            return "ERROR_OLLAMA_OFFLINE"
        except Exception as e:
            return f"ERROR_OLLAMA_EXEC: {str(e)}"
    return "ERROR_OLLAMA_TIMEOUT"

