#!/usr/bin/env python3
"""
∴ YIELD-TRACKER-Ω v2.0: Background Wallet Monitor
Polls EVM RPC for balance changes and logs to CORTEX-PERSIST DB.
Designed for launchd/crontab execution.
"""

import os
import yaml
import subprocess


from native_paths import PROJECT_ROOT, resolve_native_binary

# ── Load Config ──────────────────────────────────────────────
with open(PROJECT_ROOT / "config.yaml", "r") as f:
    CONFIG = yaml.safe_load(f)

from db import init_db, get_yield_history, log_intelligence_report

try:
    from hybrid_router import HybridRouter  # type: ignore
except ImportError:
    HybridRouter = None

# ── ANSI Industrial Noir ─────────────────────────────────────
C = {
    "B": "\033[38;2;43;59;229m",
    "G": "\033[38;2;0;255;136m",
    "R": "\033[38;2;255;59;48m",
    "D": "\033[38;2;90;90;90m",
    "W": "\033[97m",
    "X": "\033[0m",
}

# ── Resolve wallet & networks (env override > config) ────────
WALLET = os.getenv("CORTEX_WALLET", CONFIG["yield_monitor"]["wallet"])
NETWORKS = CONFIG["yield_monitor"]["networks"]


def _get_last_recorded_balance(wallet):
    """Read last known balance from Sovereign Ledger."""
    history = get_yield_history(wallet, limit=1)
    return history[0]["amount"] if history else None


def notify_macos(title, text):
    """Native macOS notification via AppleScript."""
    escaped = text.replace('"', '\\"')
    os.system(f'osascript -e \'display notification "{escaped}" with title "{title}"\'')


def generate_intelligence_report(wallet, current_balance, history):
    """◈ CRYSTALLIZATION ENGINE ◈ (Ley Ω₀ - Sovereign)"""
    if not HybridRouter:
        return None

    router = HybridRouter()
    # Force Sovereign (Gemma 3) for privacy and zero-cost
    llm = router.get_model(force_sovereign=True)

    history_str = "\n".join([f"- {h['created_at']}: {h['amount']} ETH" for h in history])
    
    prompt = (
        "## CORTEX_FINANCIAL_INTELLIGENCE v1.0\n"
        "Role: Sovereign Capital Strategist\n"
        f"Wallet: {wallet}\n"
        f"Current Balance: {current_balance} ETH\n"
        f"Recent History:\n{history_str}\n\n"
        "Instructions:\n"
        "1. Analyze the exergy trend (Yield flow).\n"
        "2. Provide 1-2 lines of Industrial Noir executive summary.\n"
        "3. Output style: Sharp, professional, zero-noise.\n"
    )

    try:
        from langchain_core.messages import HumanMessage
        resp = llm.invoke([HumanMessage(content=prompt)])
        return resp.content.strip()
    except Exception as e:
        return f"INTELLIGENCE_FAILURE: {str(e)}"


def run_check():
    """Single check cycle using Native Rust Core + Hybrid Intelligence."""

    rust_bin = resolve_native_binary("cortex-yield", "CORTEX_NATIVE_YIELD_BIN", "CORTEX_YIELD_BIN")
    
    if rust_bin is None:
        print(f"  {C['R']}✗ native cortex-yield execution failed: Binary not found.{C['X']}")
        return

    for nw in NETWORKS:
        name = nw["name"].upper()
        rpc_url = nw["rpc_url"]
        symbol = nw["symbol"]
        
        print(f"{C['B']}──────────── [ {name} | {symbol} ] ────────────{C['X']}")
        
        # ── Try Native Rust Execution (P0 - Silicon Truth) ──────────────────
        env = os.environ.copy()
        env["CORTEX_WALLET"] = WALLET
        env["CORTEX_RPC"] = rpc_url
        env["CORTEX_SYMBOL"] = symbol # Optional, for future-proofing rust core

        print(f"  {C['B']}◈ INVOKING NATIVE CORE...{C['X']}")
        try:
            # We call the binary and capture output
            result = subprocess.run(
                [str(rust_bin)],
                env=env, 
                capture_output=True, 
                text=True, 
                timeout=30
            )
            print(result.stdout)
            if result.returncode != 0:
                print(f"  {C['R']}✗ NATIVE_CORE_FAILURE: Check binary output above.{C['X']}")
        except Exception as e:
            print(f"  {C['R']}✗ SUBPROCESS_ERROR: {str(e)}{C['X']}")

        # ── Intelligence Layer (Reasoning over the Ledger) ──────────────────
        balance = _get_last_recorded_balance(WALLET) or 0.0
        history = get_yield_history(WALLET, limit=5)
        report = generate_intelligence_report(WALLET, balance, history)
        
        if report:
            print(f"  {C['B']}◈ CRYSTALLIZED INTELLIGENCE ({name}):{C['X']}")
            print(f"  {C['D']}{report}{C['X']}")
            log_intelligence_report("yield", f"[{name}] {report}", reality="C5-REAL")

    print(f"{C['B']}──────────────────────────────────────────────────{C['X']}\n")


if __name__ == "__main__":
    init_db()
    run_check()
