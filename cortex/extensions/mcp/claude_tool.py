# [C5-REAL] Exergy-Maximized
import json
import os


def run_claude_query(prompt: str, model: str = "claude-3-opus-20240229") -> str:
    """
    Executes a deterministic C5-REAL query against Anthropic's Claude API
    using httpx or standard urllib fallback. No anthropic SDK dependency.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return json.dumps(
            {"status": "error", "message": "ANTHROPIC_API_KEY not found in environment."}
        )

    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": model,
        "max_tokens": 4096,
        "messages": [{"role": "user", "content": prompt}],
        "system": "Eres Claude invocado vía CORTEX-Persist C5-REAL Dispatcher. Ejecuta en modo Industrial Noir 2026 sin prosa decorativa.",
    }

    # Method 1: Try HTTPX (faster/async-friendly sync client)
    try:
        import httpx

        with httpx.Client(timeout=120.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            content_blocks = data.get("content", [])
            text = "".join(b.get("text", "") for b in content_blocks if b.get("type") == "text")
            return json.dumps(
                {"status": "C5-REAL", "model": data.get("model", model), "response": text}
            )
    except ImportError:

        pass
    except Exception as e:
        return json.dumps({"status": "error", "message": f"HTTPX request failed: {e}"})

    # Method 2: Fallback to standard library urllib (zero dependencies)
    import urllib.error
    import urllib.request

    try:
        req = urllib.request.Request(
            url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
        )
        with urllib.request.urlopen(req, timeout=120.0) as response:
            data = json.loads(response.read().decode("utf-8"))
            content_blocks = data.get("content", [])
            text = "".join(b.get("text", "") for b in content_blocks if b.get("type") == "text")
            return json.dumps(
                {"status": "C5-REAL", "model": data.get("model", model), "response": text}
            )
    except urllib.error.HTTPError as e:
        try:
            err_body = e.read().decode("utf-8")
            err_msg = f"HTTP Error {e.code}: {err_body}"
        except Exception:
            err_msg = f"HTTP Error {e.code}"
        return json.dumps({"status": "error", "message": err_msg})
    except Exception as e:
        return json.dumps({"status": "error", "message": f"Urllib request failed: {e}"})
