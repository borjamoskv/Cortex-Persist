"""
CORTEX v6.0 — MLX Inference Server (C5-REAL)

Local inference server using Apple Silicon MLX.
OpenAI-compatible /v1/completions endpoint.
Auto-fallback to external API if local model unavailable.
"""

import json
import os
import sys
import time
from pathlib import Path

MODEL_PATH = Path("cortex-qwen-4bit")
HOST = "127.0.0.1"
PORT = 8741

# Fallback API config
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
)


def _check_model() -> bool:
    """Check if local quantized model exists."""
    return MODEL_PATH.exists() and (MODEL_PATH / "config.json").exists()


def _load_mlx_model():
    """Load model via mlx_lm. Returns (model, tokenizer) or None."""
    try:
        from mlx_lm import load

        print(f"[C5-REAL] Loading model from {MODEL_PATH}...")
        t0 = time.time()
        model, tokenizer = load(str(MODEL_PATH))
        dt = time.time() - t0
        print(f"[C5-REAL] Model loaded in {dt:.1f}s")
        return model, tokenizer
    except ImportError:
        print("[GATE] mlx_lm not installed. Run: pip install mlx-lm")
        return None
    except Exception as e:
        print(f"[ERROR] Model load failed: {e}")
        return None


def start_server():
    """Start the inference HTTP server."""
    try:
        from http.server import HTTPServer, BaseHTTPRequestHandler
    except ImportError:
        print("[ERROR] http.server unavailable")
        sys.exit(1)

    # Attempt local model load
    mlx_ctx = _load_mlx_model() if _check_model() else None
    mode = "C5-REAL (MLX Local)" if mlx_ctx else "C5-REAL (API Fallback)"
    print(f"\n[{mode}] Server starting on {HOST}:{PORT}")

    class InferenceHandler(BaseHTTPRequestHandler):
        def do_POST(self):
            if self.path == "/v1/completions":
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length)) if length else {}
                prompt = body.get("prompt", "")
                max_tokens = body.get("max_tokens", 512)
                temperature = body.get("temperature", 0.7)

                t0 = time.time()

                if mlx_ctx:
                    result = self._mlx_generate(prompt, max_tokens, temperature)
                else:
                    result = self._api_fallback(prompt, max_tokens, temperature)

                dt = time.time() - t0
                tokens_out = len(result.split())

                response = {
                    "choices": [{"text": result, "finish_reason": "stop"}],
                    "usage": {
                        "prompt_tokens": len(prompt.split()),
                        "completion_tokens": tokens_out,
                    },
                    "meta": {
                        "latency_ms": int(dt * 1000),
                        "tokens_per_sec": tokens_out / max(dt, 0.001),
                        "mode": mode,
                    },
                }
                self._send_json(200, response)

            elif self.path == "/health":
                self._send_json(200, {"status": "ok", "mode": mode})
            else:
                self._send_json(404, {"error": "not found"})

        def do_GET(self):
            if self.path == "/health":
                self._send_json(200, {"status": "ok", "mode": mode})
            else:
                self._send_json(404, {"error": "not found"})

        def _mlx_generate(self, prompt: str, max_tokens: int, temperature: float) -> str:
            try:
                from mlx_lm import generate

                model, tokenizer = mlx_ctx
                return generate(
                    model, tokenizer, prompt=prompt, max_tokens=max_tokens, temp=temperature
                )
            except Exception as e:
                return f"[MLX ERROR] {e}"

        def _api_fallback(self, prompt: str, max_tokens: int, temperature: float) -> str:
            if not GEMINI_API_KEY:
                return "[GATE] No GEMINI_API_KEY. Cannot fallback."
            try:
                import urllib.request

                data = json.dumps(
                    {
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {
                            "temperature": temperature,
                            "maxOutputTokens": max_tokens,
                        },
                    }
                ).encode()
                req = urllib.request.Request(  # noqa: S310
                    f"{GEMINI_URL}?key={GEMINI_API_KEY}",
                    data=data,
                    headers={"Content-Type": "application/json"},
                )
                with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
                    r = json.loads(resp.read())
                    return r["candidates"][0]["content"]["parts"][0]["text"]
            except Exception as e:
                return f"[API FALLBACK ERROR] {e}"

        def _send_json(self, code: int, obj: dict):
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(obj).encode())

        def log_message(self, format, *args):
            pass  # Suppress default logging

    server = HTTPServer((HOST, PORT), InferenceHandler)
    print(f"[C5-REAL] Listening on http://{HOST}:{PORT}/v1/completions")
    print(f"[C5-REAL] Health: http://{HOST}:{PORT}/health")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[C5-REAL] Server stopped.")
        server.server_close()


if __name__ == "__main__":
    start_server()
