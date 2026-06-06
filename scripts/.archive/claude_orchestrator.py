#!/usr/bin/env python3
"""
claude_orchestrator.py [C5-REAL]
Usage:
  python scripts/claude_orchestrator.py "Prompt"
  python scripts/claude_orchestrator.py -m manifest.yaml
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    import httpx
except ImportError:
    sys.exit("FATAL: httpx not installed. Run: pip install httpx")

try:
    from pydantic import BaseModel, Field, field_validator
except ImportError:
    sys.exit("FATAL: pydantic not installed. Run: pip install pydantic")

try:
    from rich.console import Console
    from rich.logging import RichHandler
    from rich.table import Table

    _RICH = True
except ImportError:
    _RICH = False

ANTHROPIC_API_URL: Final[str] = "https://api.anthropic.com/v1/messages"
ANTHROPIC_API_VERSION: Final[str] = "2023-06-01"
DEFAULT_MODEL: Final[str] = "claude-sonnet-4-20250514"
DEFAULT_MAX_TOKENS: Final[int] = 4096
MAX_RETRIES: Final[int] = 3
BACKOFF_BASE: Final[float] = 1.0
BACKOFF_CAP: Final[float] = 30.0

if _RICH:
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        handlers=[RichHandler(rich_tracebacks=True, show_path=False)],
    )
else:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

log = logging.getLogger("cortex.claude_orchestrator")
console = Console() if _RICH else None


class ClaudeRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="User prompt text")
    system: str = Field(
        default=(
            "Eres Claude invocado vía CORTEX-Persist C5-REAL Orchestrator. "
            "Ejecuta en modo señal pura: cero prosa decorativa, máxima densidad."
        ),
        description="System prompt",
    )
    model: str = Field(default=DEFAULT_MODEL)
    max_tokens: int = Field(default=DEFAULT_MAX_TOKENS, ge=1, le=128000)
    temperature: float = Field(default=0.0, ge=0.0, le=1.0)
    top_p: float | None = Field(default=None, ge=0.0, le=1.0)
    metadata: dict[str, str] = Field(default_factory=dict)

    @field_validator("model")
    @classmethod
    def validate_model(cls, v: str) -> str:
        if not v.startswith("claude-"):
            raise ValueError(f"Model must start with 'claude-', got: {v}")
        return v


class ClaudeResponse(BaseModel):
    status: str  # "C5-REAL" | "error" | "retry_exhausted"
    model: str
    request_hash: str
    content: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0
    stop_reason: str | None = None
    error: str | None = None


@dataclass
class OrchestratorStats:
    total: int = 0
    success: int = 0
    failed: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_latency_ms: float = 0.0
    results: list[ClaudeResponse] = field(default_factory=list)


def _request_hash(req: ClaudeRequest) -> str:
    blob = f"{req.model}|{req.system}|{req.prompt}|{req.temperature}".encode()
    return hashlib.sha256(blob).hexdigest()[:16]


def _build_headers(api_key: str) -> dict[str, str]:
    return {
        "x-api-key": api_key,
        "anthropic-version": ANTHROPIC_API_VERSION,
        "content-type": "application/json",
    }


def _build_payload(req: ClaudeRequest) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": req.model,
        "max_tokens": req.max_tokens,
        "temperature": req.temperature,
        "system": req.system,
        "messages": [{"role": "user", "content": req.prompt}],
    }
    if req.top_p is not None:
        payload["top_p"] = req.top_p
    if req.metadata:
        payload["metadata"] = {"user_id": req.metadata.get("user_id", "cortex-orchestrator")}
    return payload


async def dispatch_single(
    client: httpx.AsyncClient,
    req: ClaudeRequest,
    api_key: str,
    *,
    stream: bool = False,
) -> ClaudeResponse:
    headers = _build_headers(api_key)
    payload = _build_payload(req)
    rhash = _request_hash(req)

    log.info("[DISPATCH] hash=%s model=%s temp=%.2f", rhash, req.model, req.temperature)

    last_error: str | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        t0 = time.monotonic()
        try:
            if stream:
                return await _dispatch_stream(client, headers, payload, rhash, req.model, t0)

            resp = await client.post(ANTHROPIC_API_URL, headers=headers, json=payload)

            if resp.status_code == 429:
                retry_after = float(resp.headers.get("retry-after", BACKOFF_BASE * attempt))
                log.warning(
                    "[RATE-LIMIT] Retry-After=%.1fs attempt=%d/%d",
                    retry_after,
                    attempt,
                    MAX_RETRIES,
                )
                await asyncio.sleep(retry_after)
                continue

            if resp.status_code >= 500:
                delay = min(BACKOFF_BASE * (2 ** (attempt - 1)), BACKOFF_CAP)
                log.warning(
                    "[SERVER-ERR] %d - backoff=%.1fs attempt=%d/%d",
                    resp.status_code,
                    delay,
                    attempt,
                    MAX_RETRIES,
                )
                await asyncio.sleep(delay)
                continue

            resp.raise_for_status()
            data = resp.json()
            latency = (time.monotonic() - t0) * 1000

            content_blocks = data.get("content", [])
            text = "".join(b.get("text", "") for b in content_blocks if b.get("type") == "text")
            usage = data.get("usage", {})

            result = ClaudeResponse(
                status="C5-REAL",
                model=data.get("model", req.model),
                request_hash=rhash,
                content=text,
                input_tokens=usage.get("input_tokens", 0),
                output_tokens=usage.get("output_tokens", 0),
                latency_ms=round(latency, 2),
                stop_reason=data.get("stop_reason"),
            )
            log.info(
                "[OK] hash=%s tokens=%d+%d latency=%.0fms stop=%s",
                rhash,
                result.input_tokens,
                result.output_tokens,
                result.latency_ms,
                result.stop_reason,
            )
            return result

        except httpx.HTTPStatusError as e:
            last_error = f"HTTP {e.response.status_code}: {e.response.text[:300]}"
            log.error("[HTTP-ERR] %s attempt=%d/%d", last_error, attempt, MAX_RETRIES)
        except httpx.ConnectError as e:
            last_error = f"Connection failed: {e}"
            log.error("[CONN-ERR] %s attempt=%d/%d", last_error, attempt, MAX_RETRIES)
        except Exception as e:
            last_error = f"{type(e).__name__}: {e}"
            log.error("[ERR] %s attempt=%d/%d", last_error, attempt, MAX_RETRIES)

        if attempt < MAX_RETRIES:
            delay = min(BACKOFF_BASE * (2 ** (attempt - 1)), BACKOFF_CAP)
            await asyncio.sleep(delay)

    return ClaudeResponse(
        status="retry_exhausted",
        model=req.model,
        request_hash=rhash,
        content="",
        error=last_error or "All retries exhausted",
    )


async def _dispatch_stream(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    payload: dict[str, Any],
    rhash: str,
    model: str,
    t0: float,
) -> ClaudeResponse:
    payload["stream"] = True
    chunks: list[str] = []
    input_tokens = 0
    output_tokens = 0
    stop_reason = None

    async with client.stream("POST", ANTHROPIC_API_URL, headers=headers, json=payload) as resp:
        resp.raise_for_status()
        async for line in resp.aiter_lines():
            if not line.startswith("data: "):
                continue
            data_str = line[6:].strip()
            if data_str == "[DONE]":
                break
            try:
                event = json.loads(data_str)
                etype = event.get("type", "")
                if etype == "content_block_delta":
                    delta = event.get("delta", {})
                    if delta.get("type") == "text_delta":
                        text = delta.get("text", "")
                        chunks.append(text)
                        if console:
                            console.print(text, end="", highlight=False)
                        else:
                            sys.stdout.write(text)
                            sys.stdout.flush()
                elif etype == "message_start":
                    usage = event.get("message", {}).get("usage", {})
                    input_tokens = usage.get("input_tokens", 0)
                elif etype == "message_delta":
                    usage = event.get("usage", {})
                    output_tokens = usage.get("output_tokens", 0)
                    stop_reason = event.get("delta", {}).get("stop_reason")
            except json.JSONDecodeError:
                continue

    if console:
        console.print()  # Newline after stream
    else:
        sys.stdout.write("\n")

    latency = (time.monotonic() - t0) * 1000
    return ClaudeResponse(
        status="C5-REAL",
        model=model,
        request_hash=rhash,
        content="".join(chunks),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=round(latency, 2),
        stop_reason=stop_reason,
    )


async def dispatch_batch(
    requests: list[ClaudeRequest],
    api_key: str,
    *,
    concurrency: int = 3,
    stream: bool = False,
) -> OrchestratorStats:
    stats = OrchestratorStats(total=len(requests))
    semaphore = asyncio.Semaphore(concurrency)

    async with httpx.AsyncClient(timeout=120.0) as client:

        async def _run(req: ClaudeRequest) -> ClaudeResponse:
            async with semaphore:
                return await dispatch_single(client, req, api_key, stream=stream)

        tasks = [asyncio.create_task(_run(r)) for r in requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for r in results:
            if isinstance(r, Exception):
                stats.failed += 1
                stats.results.append(
                    ClaudeResponse(
                        status="error",
                        model="unknown",
                        request_hash="exception",
                        content="",
                        error=str(r),
                    )
                )
            else:
                if r.status == "C5-REAL":
                    stats.success += 1
                else:
                    stats.failed += 1
                stats.total_input_tokens += r.input_tokens
                stats.total_output_tokens += r.output_tokens
                stats.total_latency_ms += r.latency_ms
                stats.results.append(r)

    return stats


def load_manifest(path: str) -> list[ClaudeRequest]:
    try:
        import yaml
    except ImportError:
        sys.exit("FATAL: PyYAML required for manifest loading. Run: pip install pyyaml")

    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict) or "requests" not in data:
        sys.exit(f"FATAL: Invalid manifest format in {path}. Expected 'requests' key.")

    defaults = data.get("defaults", {})
    requests: list[ClaudeRequest] = []

    for item in data["requests"]:
        merged = {**defaults, **item}
        requests.append(ClaudeRequest(**merged))

    return requests


def render_stats(stats: OrchestratorStats) -> None:
    if console:
        table = Table(title="Claude Orchestrator - C5-REAL Results", show_lines=True)
        table.add_column("#", justify="right", style="dim")
        table.add_column("Hash", style="cyan")
        table.add_column("Status", style="bold")
        table.add_column("Model", style="green")
        table.add_column("Tokens (in+out)", justify="right")
        table.add_column("Latency", justify="right", style="yellow")
        table.add_column("Stop", style="dim")

        for i, r in enumerate(stats.results, 1):
            status_style = "green" if r.status == "C5-REAL" else "red"
            table.add_row(
                str(i),
                r.request_hash,
                f"[{status_style}]{r.status}[/{status_style}]",
                r.model,
                f"{r.input_tokens}+{r.output_tokens}",
                f"{r.latency_ms:.0f}ms",
                r.stop_reason or r.error or "-",
            )

        console.print(table)
        console.print(
            f"\n[bold]Totals:[/bold] {stats.success}/{stats.total} OK | "
            f"Tokens: {stats.total_input_tokens}+{stats.total_output_tokens} | "
            f"Latency: {stats.total_latency_ms:.0f}ms"
        )
    else:
        log.info("Results: %d/%d OK", stats.success, stats.total)
        for r in stats.results:
            log.info("  %s | %s | %s", r.request_hash, r.status, r.model)


def write_output(stats: OrchestratorStats, path: str) -> None:
    output = {
        "reality_level": "C5-REAL",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "summary": {
            "total": stats.total,
            "success": stats.success,
            "failed": stats.failed,
            "total_input_tokens": stats.total_input_tokens,
            "total_output_tokens": stats.total_output_tokens,
            "total_latency_ms": round(stats.total_latency_ms, 2),
        },
        "results": [r.model_dump() for r in stats.results],
    }
    Path(path).write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info("[WRITE] Output → %s", path)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="claude_orchestrator",
        description="C5-REAL Deterministic Claude API Orchestrator",
    )
    p.add_argument("prompt", nargs="?", help="Single prompt to dispatch")
    p.add_argument("--manifest", "-m", help="YAML manifest for batch dispatch")
    p.add_argument("--model", default=DEFAULT_MODEL, help=f"Model ID (default: {DEFAULT_MODEL})")
    p.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS, help="Max output tokens")
    p.add_argument(
        "--temperature", "-t", type=float, default=0.0, help="Temperature (0.0 = deterministic)"
    )
    p.add_argument("--system", "-s", help="Custom system prompt")
    p.add_argument("--output", "-o", help="Output JSON file path")
    p.add_argument("--concurrency", "-c", type=int, default=3, help="Batch concurrency limit")
    p.add_argument("--stream", action="store_true", help="Enable SSE streaming output")
    p.add_argument("--verbose", "-v", action="store_true", help="Debug logging")
    return p.parse_args()


async def main() -> None:
    args = parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Resolve API key
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        sys.exit("FATAL: ANTHROPIC_API_KEY not set.\n  export ANTHROPIC_API_KEY=sk-ant-...")

    # Build request(s)
    if args.manifest:
        requests = load_manifest(args.manifest)
        log.info("[MANIFEST] Loaded %d requests from %s", len(requests), args.manifest)
    elif args.prompt:
        req_kwargs: dict[str, Any] = {
            "prompt": args.prompt,
            "model": args.model,
            "max_tokens": args.max_tokens,
            "temperature": args.temperature,
        }
        if args.system:
            req_kwargs["system"] = args.system
        requests = [ClaudeRequest(**req_kwargs)]
    else:
        sys.exit("FATAL: Provide a prompt or --manifest. Use -h for help.")

    # Dispatch
    if len(requests) == 1 and not args.manifest:
        async with httpx.AsyncClient(timeout=120.0) as client:
            result = await dispatch_single(client, requests[0], api_key, stream=args.stream)
            stats = OrchestratorStats(
                total=1,
                success=1 if result.status == "C5-REAL" else 0,
                failed=0 if result.status == "C5-REAL" else 1,
                total_input_tokens=result.input_tokens,
                total_output_tokens=result.output_tokens,
                total_latency_ms=result.latency_ms,
                results=[result],
            )

            # Single mode: print content directly
            if not args.stream and result.status == "C5-REAL":
                if console:
                    console.print(f"\n[bold cyan]── Response ──[/bold cyan]\n{result.content}")
                else:
                    sys.stdout.write(f"\n{result.content}\n")
            elif result.status != "C5-REAL":
                log.error("[FAIL] %s", result.error)
    else:
        stats = await dispatch_batch(
            requests, api_key, concurrency=args.concurrency, stream=args.stream
        )

    # Output
    render_stats(stats)
    if args.output:
        write_output(stats, args.output)


if __name__ == "__main__":
    asyncio.run(main())
