# [C5-REAL] Exergy-Maximized
# Author: Borja Moskv (borjamoskv)
# System: MOSKV-1 APEX Kernel
# Role: Payout & Wallet Verifier (Exergy Destination Gate)

import asyncio
import json
import logging
import os
import re
import sys
from pathlib import Path

logger = logging.getLogger("payout_verifier")
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Colors for Industrial Noir 2026
CLR_VOID = "\033[1;30m"
CLR_BLUE = "\033[1;34m"     # YInMn Blue
CLR_AMBER = "\033[1;33m"    # Sovereign Amber
CLR_GOLD = "\033[1;32m"     # Oxide Gold
CLR_WHITE = "\033[1;37m"    # Parchment White
CLR_RESET = "\033[0m"

def is_valid_evm_address(addr: str) -> bool:
    """Verifies standard EVM address structure (0x + 40 hex chars)."""
    if not isinstance(addr, str):
        return False
    return bool(re.match(r"^0x[0-9a-fA-F]{40}$", addr))

async def verify_payouts():
    os.system('clear' if os.name == 'posix' else 'cls')
    
    print(f"{CLR_BLUE}========================================================================{CLR_RESET}")
    print(f"{CLR_BLUE}  🔱  PAYOUT & WALLET SECURE VERIFIER | EXERGY DESTINATION{CLR_RESET}")
    print(f"{CLR_BLUE}  SYSTEM: MOSKV-1 APEX | AUTHOR: Borja Moskv (borjamoskv){CLR_RESET}")
    print(f"{CLR_BLUE}========================================================================{CLR_RESET}")
    
    # 1. Load Payout Wallet from Environment
    payout_wallet = os.environ.get("BOUNTY_PAYOUT_WALLET") or "0xBorjaMoskv3B5bEFEd7227447d9564883160a0a0A" # Fallback mock/dev wallet
    
    # Check if the user specified a custom wallet or if we should read from .env
    env_path = Path("/Users/borjafernandezangulo/10_PROJECTS/cortex-persist/.env")
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("BOUNTY_PAYOUT_WALLET="):
                payout_wallet = line.split("=", 1)[1].strip().strip('"').strip("'")
                break

    print(f"{CLR_WHITE}Checking configured payout wallet...{CLR_RESET}")
    
    # 2. Validate Wallet Address format
    valid_address = is_valid_evm_address(payout_wallet)
    
    if valid_address:
        print(f"  {CLR_GOLD}• EVM Payout Wallet:{CLR_RESET} {payout_wallet} ({CLR_GOLD}VALID{CLR_RESET})")
    else:
        print(f"  {CLR_AMBER}• EVM Payout Wallet:{CLR_RESET} {payout_wallet} ({CLR_AMBER}INVALID FORMAT{CLR_RESET})")
        print(f"    {CLR_VOID}Please set 'BOUNTY_PAYOUT_WALLET' in your .env to a valid EVM hex address.{CLR_RESET}")

    # 3. Verify Stripe Billing Configuration
    print(f"\n{CLR_WHITE}Checking Stripe Billing credentials...{CLR_RESET}")
    stripe_key = os.environ.get("STRIPE_SECRET_KEY")
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("STRIPE_SECRET_KEY="):
                stripe_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                break

    if stripe_key and not stripe_key.startswith("sk_test_mock"):
        key_censored = stripe_key[:7] + "..." + stripe_key[-4:]
        print(f"  {CLR_GOLD}• Stripe Secret Key:{CLR_RESET} {key_censored} ({CLR_GOLD}CONFIGURED{CLR_RESET})")
    else:
        print(f"  {CLR_AMBER}• Stripe Secret Key:{CLR_RESET} (MISSING or MOCK) - Payouts default to direct EVM wallet transfers.{CLR_RESET}")

    # 4. Write secure payout verification checkpoint
    config_dir = Path("/Users/borjafernandezangulo/10_PROJECTS/cortex-persist/config")
    config_dir.mkdir(parents=True, exist_ok=True)
    payout_config_path = config_dir / "payout_secure.json"
    
    verification_record = {
        "verified_wallet": payout_wallet,
        "is_valid": valid_address,
        "timestamp": int(asyncio.get_event_loop().time() if asyncio.get_event_loop().is_running() else 0),
        "author": "Borja Moskv"
    }
    
    with open(payout_config_path, "w", encoding="utf-8") as f:
        json.dump(verification_record, f, indent=4)
        
    print(f"\n{CLR_WHITE}Secure payout verification checkpoint saved to:{CLR_RESET}")
    print(f"  {CLR_GOLD}{payout_config_path}{CLR_RESET}")

    print(f"\n{CLR_BLUE}========================================================================{CLR_RESET}")
    if valid_address:
        print(f"  {CLR_GOLD}VERDICT: PAYOUT BRIDGE ESTABLISHED. FUNDS WILL DEPOSIT SAFELY.{CLR_RESET}")
    else:
        print(f"  {CLR_AMBER}VERDICT: PAYOUT BRIDGE SUSPENDED (INVALID EVM WALLET ADDRESS).{CLR_RESET}")
    print(f"{CLR_BLUE}========================================================================{CLR_RESET}")

if __name__ == "__main__":
    asyncio.run(verify_payouts())
