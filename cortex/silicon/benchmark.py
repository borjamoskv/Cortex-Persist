"""
CORTEX v6.0 — Silicon vs API Benchmark (C5-REAL)

Compares MLX local inference against external APIs.
Outputs latency, throughput, and quality metrics.
"""

import json
import os
import time
from pathlib import Path

PROMPTS = [
    "Explain the reentrancy vulnerability in Solidity smart contracts. Be concise.",
    "Write a Python function that detects integer overflow in a uint256 variable.",
    "What is the difference between delegatecall and call in the EVM?",
    "Describe how flash loans enable arbitrage in DeFi protocols.",
    "Analyze this Solidity pattern for access control issues:\n"
    "function withdraw() public { require(balances[msg.sender] > 0); "
    "(bool ok,) = msg.sender.call{value: balances[msg.sender]}(''); "
    "require(ok); balances[msg.sender] = 0; }",
]

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
)
MLX_URL = "http://127.0.0.1:8741/v1/completions"


def _bench_mlx(prompt: str) -> dict:
    """Benchmark local MLX server."""
    try:
        import urllib.request

        data = json.dumps({"prompt": prompt, "max_tokens": 256, "temperature": 0.3}).encode()
        req = urllib.request.Request(  # noqa: S310
            MLX_URL, data=data, headers={"Content-Type": "application/json"}
        )
        t0 = time.time()
        with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
            r = json.loads(resp.read())
            dt = time.time() - t0
            text = r["choices"][0]["text"]
            meta = r.get("meta", {})
            return {
                "source": "MLX-Local",
                "latency_ms": int(dt * 1000),
                "tokens_per_sec": meta.get("tokens_per_sec", len(text.split()) / max(dt, 0.001)),
                "output_len": len(text),
                "ok": True,
            }
    except Exception as e:
        return {"source": "MLX-Local", "ok": False, "error": str(e)}


def _bench_gemini(prompt: str) -> dict:
    """Benchmark Gemini API."""
    if not GEMINI_API_KEY:
        return {"source": "Gemini-API", "ok": False, "error": "No GEMINI_API_KEY"}
    try:
        import urllib.request

        data = json.dumps(
            {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.3, "maxOutputTokens": 256},
            }
        ).encode()
        req = urllib.request.Request(  # noqa: S310
            f"{GEMINI_URL}?key={GEMINI_API_KEY}",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        t0 = time.time()
        with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
            r = json.loads(resp.read())
            dt = time.time() - t0
            text = r["candidates"][0]["content"]["parts"][0]["text"]
            return {
                "source": "Gemini-API",
                "latency_ms": int(dt * 1000),
                "tokens_per_sec": len(text.split()) / max(dt, 0.001),
                "output_len": len(text),
                "ok": True,
            }
    except Exception as e:
        return {"source": "Gemini-API", "ok": False, "error": str(e)}


def run_benchmark():
    """Run full benchmark suite."""
    print(f"\n{'=' * 70}")
    print("CORTEX Silicon Benchmark — C5-REAL")
    print(f"{'=' * 70}\n")

    results = {"mlx": [], "gemini": []}

    for i, prompt in enumerate(PROMPTS):
        print(f"[Prompt {i + 1}/{len(PROMPTS)}] {prompt[:60]}...")

        m = _bench_mlx(prompt)
        results["mlx"].append(m)
        if m["ok"]:
            print(
                f"  MLX:    {m['latency_ms']:>6}ms | {m['tokens_per_sec']:>6.1f} tok/s | {m['output_len']} chars"
            )
        else:
            print(f"  MLX:    UNAVAILABLE — {m.get('error', '')[:50]}")

        g = _bench_gemini(prompt)
        results["gemini"].append(g)
        if g["ok"]:
            print(
                f"  Gemini: {g['latency_ms']:>6}ms | {g['tokens_per_sec']:>6.1f} tok/s | {g['output_len']} chars"
            )
        else:
            print(f"  Gemini: UNAVAILABLE — {g.get('error', '')[:50]}")

        time.sleep(0.5)

    # Summary
    print(f"\n{'=' * 70}")
    print("SUMMARY")
    print(f"{'=' * 70}")

    for src, key in [("MLX-Local", "mlx"), ("Gemini-API", "gemini")]:
        ok = [r for r in results[key] if r.get("ok")]
        if ok:
            avg_lat = sum(r["latency_ms"] for r in ok) / len(ok)
            avg_tps = sum(r["tokens_per_sec"] for r in ok) / len(ok)
            print(
                f"  {src:<12} | Avg Latency: {avg_lat:>6.0f}ms | Avg Throughput: {avg_tps:>6.1f} tok/s | {len(ok)}/{len(PROMPTS)} ok"
            )
        else:
            print(f"  {src:<12} | UNAVAILABLE")

    # Save results
    out = Path("scratch/benchmark_results.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n[C5-REAL] Results saved to {out}")


if __name__ == "__main__":
    run_benchmark()
