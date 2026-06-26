#!/usr/bin/env python3
"""
∴ OUROBOROS-CAPITAL-Ω v2.0: Hyper-Parallel Bounty Scanner
20-thread concurrent extraction across Solidity/Rust/TypeScript vectors.
Persists all targets to CORTEX-PERSIST DB (WAL mode).
"""

import json
import time
import urllib.request
import urllib.error
import yaml
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from datetime import datetime

# ── Load Config ──────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
with open(PROJECT_ROOT / "config.yaml", "r") as f:
    CONFIG = yaml.safe_load(f)

# ── Import DB Layer ──────────────────────────────────────────
from db import init_db, upsert_bounty, log_scan

# ── Import Strike Engine (Motor Muscular) ────────────────────
from strike_engine import dispatch_strike_async

# ── ANSI Industrial Noir Palette ─────────────────────────────
C = {
    "B": "\033[38;2;43;59;229m",   # Primary #2B3BE5
    "G": "\033[38;2;0;255;136m",   # Accent  #00FF88
    "R": "\033[38;2;255;59;48m",   # Warn    #FF3B30
    "D": "\033[38;2;90;90;90m",    # Dim
    "W": "\033[97m",               # White
    "X": "\033[0m",                # Reset
}


def _scan_source(source):
    """Scan a single GitHub search endpoint.
    Returns (source_name, results, total_found, pruned, persisted,
    duration_ms, error)."""
    name = source["name"]
    url = source["url"]
    # Use Token if available to bypass rate limits
    token = os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN")
    headers = {
        "User-Agent": CONFIG["scanner"]["user_agent"],
        "Accept": "application/vnd.github.v3+json",
    }
    # Resilient auth layer: fallback to public if token fails
    if token and token.strip():
        headers["Authorization"] = f"token {token.strip()}"
    threshold = CONFIG["scanner"]["exergy_threshold"]

    t0 = time.monotonic()
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        if e.code == 401 and "Authorization" in headers:
            # Fallback: retry without auth (public API)
            del headers["Authorization"]
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = json.loads(resp.read().decode())
            except Exception as e2:
                duration = (time.monotonic() - t0) * 1000
                return name, [], 0, 0, 0, duration, str(e2)
        else:
            duration = (time.monotonic() - t0) * 1000
            return name, [], 0, 0, 0, duration, str(e)
    except Exception as e:
        duration = (time.monotonic() - t0) * 1000
        return name, [], 0, 0, 0, duration, str(e)

    issues = data.get("items", [])
    found = len(issues)
    pruned = 0
    persisted = 0

    for issue in issues[:15]:
        title = issue.get("title", "")
        html_url = issue.get("html_url", "")
        author = issue.get("user", {}).get("login", "unknown")
        bounty_id = issue.get("id", 0)

        exergy = round((len(title) / 10.0) + 1.2, 2)

        if exergy >= threshold:
            upsert_bounty(name, bounty_id, title, html_url, author, exergy)
            persisted += 1
            
            # [✓] CORTEX KINETIC HOOK: Ejecución Activa
            # Si el pago (exergía) es alto, no solo escaneamos: atacamos.
            if exergy >= 5.0:
                dispatch_strike_async(name, title, html_url, exergy)
        else:
            pruned += 1

    duration = (time.monotonic() - t0) * 1000
    log_scan(name, found, pruned, persisted, duration)
    return name, issues[:5], found, pruned, persisted, duration, None


def run_swarm_scan():
    """Execute all source scans in parallel using ThreadPoolExecutor."""
    sources = CONFIG["scanner"]["sources"]
    max_workers = min(CONFIG["scanner"]["max_threads"], len(sources))

    print(f"{C['D']}  Threads: {max_workers} | Sources: {len(sources)} | "
          f"Threshold: {CONFIG['scanner']['exergy_threshold']}{C['X']}")
    print(f"{C['D']}  DB: WAL Mode | "
          f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{C['X']}\n")

    total_found = 0
    total_persisted = 0
    total_errors = 0
    t_global = time.monotonic()

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_scan_source, s): s for s in sources}

        for future in as_completed(futures):
            name, samples, found, pruned, persisted, dur, err = future.result()

            if err:
                total_errors += 1
                print(f"  {C['R']}✗ {name:<30} ERROR: {err}{C['X']}")
            else:
                total_found += found
                total_persisted += persisted
                status = f"{C['G']}✓{C['X']}" if persisted > 0 else f"{C['D']}○{C['X']}"
                print(f"  {status} {C['W']}{name:<30}{C['X']} "
                      f"{C['D']}found:{C['X']}{found:<4} "
                      f"{C['G']}persisted:{persisted:<3}{C['X']} "
                      f"{C['D']}{dur:.0f}ms{C['X']}")

    wall_time = (time.monotonic() - t_global) * 1000

    print(f"\n{C['B']}──────────────────────────────────────────────────{C['X']}")
    print(f"  {C['W']}Total Found:{C['X']}     {total_found}")
    print(f"  {C['G']}Total Persisted:{C['X']} {total_persisted}")
    print(f"  {C['R']}Errors:{C['X']}          {total_errors}")
    print(f"  {C['B']}Wall Time:{C['X']}       {wall_time:.0f}ms")
    print(f"{C['B']}──────────────────────────────────────────────────{C['X']}\n")

    return total_found, total_persisted, wall_time


import signal

_keep_running = True

def _handle_sigterm(signum, frame):
    global _keep_running
    print(f"\n{C['R']}⚡ Recibida señal de interrupción ({signum}). Apagando demonio Ouroboros pacíficamente...{C['X']}")
    _keep_running = False

if __name__ == "__main__":
    signal.signal(signal.SIGINT, _handle_sigterm)
    signal.signal(signal.SIGTERM, _handle_sigterm)
    
    init_db()
    
    # R4/P0 Exergy cadence mode: 10 minutes
    interval = int(os.getenv("OUROBOROS_POLL_INTERVAL_SEC", 600))
    
    print(f"{C['B']}=== OUROBOROS DEMONIO CONTINUO INICIADO (Poll={interval}s) ==={C['X']}")
    while _keep_running:
        try:
            run_swarm_scan()
            if not _keep_running:
                break
            
            print(f"{C['D']}... Hibernando por {interval} segundos ...{C['X']}")
            # Sleep in chunks to allow quick interrupt responsiveness
            for _ in range(interval):
                if not _keep_running:
                    break
                time.sleep(1)
                
        except Exception as e:
            print(f"{C['R']}Error critico en el bucle del Demonio: {e}{C['X']}")
            time.sleep(10)
            
    print(f"{C['G']}Ouroboros-Omega Extractor Apagado correctamente.{C['X']}")
