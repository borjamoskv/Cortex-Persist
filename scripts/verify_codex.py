import asyncio
import argparse
import os
import sys
import time

import httpx
from dotenv import load_dotenv

# Ensure we can import from local cortex
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from cortex.async_client import AsyncCortexClient

load_dotenv()

# --- Aesthetic Tokens ---
COLOR_ACCENT = "\033[38;2;0;220;180m"  # Cyber Lime/Teal
COLOR_DIM = "\033[38;2;100;100;100m"
COLOR_ERR = "\033[38;2;255;50;50m"
COLOR_RESET = "\033[0m"
COLOR_BOLD = "\033[1m"


async def verify_codex(host: str, port: int, limit: int):
    api_key = os.environ.get("CORTEX_API_KEY")
    base_url = f"http://{host}:{port}"
    
    print(f"{COLOR_DIM}┌─{COLOR_RESET} {COLOR_BOLD}CODEX VERIFICATION PROTOCOL{COLOR_RESET} {COLOR_DIM}─────────────────────────{COLOR_RESET}")
    print(f"{COLOR_DIM}│{COLOR_RESET} TARGET : {COLOR_ACCENT}{base_url}{COLOR_RESET}")
    print(f"{COLOR_DIM}│{COLOR_RESET} LIMIT  : {limit} facts")
    print(f"{COLOR_DIM}└──────────────────────────────────────────────────────{COLOR_RESET}")

    start_time = time.perf_counter()
    client = AsyncCortexClient(api_token=api_key, base_url=base_url)

    try:
        # Check status
        status_start = time.perf_counter()
        status = await client.status()
        status_ms = (time.perf_counter() - status_start) * 1000
        print(f" {COLOR_ACCENT}✦{COLOR_RESET} Neural Link Active (v{status.get('version', 'unknown')}) {COLOR_DIM}[{status_ms:.2f}ms]{COLOR_RESET}")
        
        # Recall recent facts to verify storage
        print(f" {COLOR_DIM}▸{COLOR_RESET} Scanning memory banks...")
        fetch_start = time.perf_counter()
        results = await client.recall(project="cortex", limit=limit)
        fetch_ms = (time.perf_counter() - fetch_start) * 1000

        print(f" {COLOR_ACCENT}✦{COLOR_RESET} Found {len(results)} active facts {COLOR_DIM}[{fetch_ms:.2f}ms]{COLOR_RESET}")
        
        for res in results:
            content_preview = res.content[:80].replace("\n", " ").strip()
            print(f"   {COLOR_DIM}├─{COLOR_RESET} [{res.fact_type.upper():<10}] {COLOR_DIM}ID:{res.id:<4}{COLOR_RESET} {content_preview}...")
            
        total_time = (time.perf_counter() - start_time) * 1000
        print(f"\n{COLOR_ACCENT}VERIFICATION COMPLETE{COLOR_RESET} {COLOR_DIM}:: Total Latency: {total_time:.2f}ms{COLOR_RESET}")

    except httpx.ConnectError:
        print(f"\n{COLOR_ERR}CRITICAL FAILURE{COLOR_RESET}: Could not connect to CORTEX daemon at {base_url}")
        print(f"{COLOR_DIM}Ensure the daemon is running (`cortex daemon start`).{COLOR_RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{COLOR_ERR}VERIFICATION FAILED{COLOR_RESET}: {e}")
        sys.exit(1)
    finally:
        await client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify CORTEX CODEX integrity.")
    parser.add_argument("--host", default="127.0.0.1", help="CORTEX daemon host")
    parser.add_argument("--port", type=int, default=8000, help="CORTEX daemon port")
    parser.add_argument("--limit", type=int, default=10, help="Number of facts to recall")
    
    args = parser.parse_args()
    
    try:
        asyncio.run(verify_codex(host=args.host, port=args.port, limit=args.limit))
    except KeyboardInterrupt:
        print(f"\n{COLOR_DIM}Verification aborted by user.{COLOR_RESET}")
        sys.exit(0)
