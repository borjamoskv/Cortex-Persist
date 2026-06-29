# [C5-REAL] Exergy-Maximized
"""
CORTEX Extension Registry & Tier System
Author: Borja Moskv

Manages the lifecycle, activation, and loading rules for all 77 extensions.
Enforces sandbox boundaries and logs warnings/errors for experimental modules.
"""

import logging
import os
import sys

logger = logging.getLogger("cortex.extensions.registry")

# Extension classification mapping
TIER_MAP = {
    # CORE: Always allowed, critical path
    "llm": "CORE",
    "swarm": "CORE",
    "mcp": "CORE",
    "agents": "CORE",
    "security": "CORE",
    "timing": "CORE",
    "git": "CORE",
    "platform": "CORE",
    "adk": "CORE",
    "daemon": "CORE",
    "nexus": "CORE",
    
    # OPTIONAL: Allowed, but lazy-loaded and monitored
    "browser": "OPTIONAL",
    "audio": "OPTIONAL",
    "compliance": "OPTIONAL",
    "fingerprint": "OPTIONAL",
    "signals": "OPTIONAL",
    "causality": "OPTIONAL",
    "context": "OPTIONAL",
    "episodic": "OPTIONAL",
    "evolution": "OPTIONAL",
    "federation": "OPTIONAL",
    "health": "OPTIONAL",
    "immune": "OPTIONAL",
    "notifications": "OPTIONAL",
    "perception": "OPTIONAL",
    "policy": "OPTIONAL",
    "protocols": "OPTIONAL",
    "scraper": "OPTIONAL",
    "songlines": "OPTIONAL",
    "sync": "OPTIONAL",
    "skills": "OPTIONAL",
    "trust": "OPTIONAL",
    
    # EXPERIMENTAL: Forbidden or strict warning unless CORTEX_EXPERIMENTAL_EXTENSIONS=1
    "dopamine_loop": "EXPERIMENTAL",
    "wealth": "EXPERIMENTAL",
    "bci": "EXPERIMENTAL",
    "aether": "EXPERIMENTAL",
    "cuatrida": "EXPERIMENTAL",
    "aether_omega": "EXPERIMENTAL",
    "web3": "EXPERIMENTAL",
    "zkortex": "EXPERIMENTAL",
    "manifold": "EXPERIMENTAL",
    "market_maker": "EXPERIMENTAL",
    "mejoralo": "EXPERIMENTAL",
    "nous": "EXPERIMENTAL",
    "shannon": "EXPERIMENTAL",
    "substrate": "EXPERIMENTAL",
    "taas": "EXPERIMENTAL",
    "ttt": "EXPERIMENTAL",
    "tutor_agent": "EXPERIMENTAL",
    "ui_control": "EXPERIMENTAL",
    "vex": "EXPERIMENTAL",
    "genesis": "EXPERIMENTAL",
}

def get_tier(extension_name: str) -> str:
    """Get the tier of a specific extension name."""
    return TIER_MAP.get(extension_name, "EXPERIMENTAL")  # Default to experimental for safety

_warned_extensions = set()

def verify_extension_import(fullname: str) -> None:
    """Enforce import permissions and environmental flags for extensions."""
    parts = fullname.split(".")
    if len(parts) < 3 or parts[0] != "cortex" or parts[1] != "extensions":
        return
    
    ext_name = parts[2]
    tier = get_tier(ext_name)
    
    if tier == "EXPERIMENTAL":
        enabled = os.environ.get("CORTEX_EXPERIMENTAL_EXTENSIONS", "0") == "1"
        if not enabled:
            if ext_name in _warned_extensions:
                return
            _warned_extensions.add(ext_name)
            
            # Under strict C5-REAL, we warn clearly or raise depending on a strict flag
            strict = os.environ.get("CORTEX_STRICT_EXTENSIONS", "0") == "1"
            msg = (
                f"[C5-REAL] WARNING: Importing experimental extension '{ext_name}' "
                f"without CORTEX_EXPERIMENTAL_EXTENSIONS=1 env var context."
            )
            if strict:
                raise ImportError(
                    f"Blocked import of experimental extension '{ext_name}' in strict mode. "
                    f"Set CORTEX_EXPERIMENTAL_EXTENSIONS=1 to allow."
                )
            else:
                logger.warning(msg)
                # Fallback to direct stderr write to ensure visibility in console logs
                sys.stderr.write(f"\033[93m{msg}\033[0m\n")
