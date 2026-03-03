"""
CORTEX Naming Manifold — Sovereign Identity Generation.
Generates high-authority names for the MOSKV-1 enjambre.
"""

import random
import secrets
import string

PREFIXES = [
    "Sovereign", "Legion", "Ghost", "Spectre", "Vector", "Nexus", "Proxy", "Oracle",
    "Sentinel", "Phantom", "Aether", "Chronos", "Keter", "Aleph", "Omega", "Centauro",
    "Ouroboros", "Phoenix", "Chimera", "Leviathan", "Shadow", "Cipher", "Void", "Matrix",
    "Iron", "Chrome", "Neo", "Deep", "Silent", "Active", "Static", "Binary"
]

CORES = [
    "Architect", "Sentinel", "Auditor", "Hunter", "Weaver", "Operator", "Researcher",
    "Designer", "Strategist", "Scout", "Watcher", "Enforcer", "Mediator", "Infiltrator",
    "Guardian", "Prophet", "Navigator", "Scribe", "Mechanic", "Surgeon", "Analyst",
    "Node", "Core", "Pulse", "Signal", "Fragment", "Ghost", "Echo"
]

SUFFIXES = [
    "Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta", "Eta", "Theta", "Iota", "Kappa",
    "Lambda", "Mu", "Nu", "Xi", "Omicron", "Pi", "Rho", "Sigma", "Tau", "Upsilon", "Phi",
    "Chi", "Psi", "Omega", "Prime", "Zero", "One", "IX", "X", "XV", "MAX", "MIN", "PRO"
]

SPECIALTY_CORES = {
    "code": ["Architect", "Weaver", "Scribe", "Node"],
    "security": ["Auditor", "Guardian", "Enforcer", "Sentinel"],
    "intel": ["Scout", "Watcher", "Infiltrator", "Signal"],
    "data": ["Analyst", "Researcher", "Mechanic", "Fragment"],
    "creative": ["Designer", "Architect", "Echo", "Pulse"],
    "marketing": ["Strategist", "Navigatior", "Prophet", "Signal"],
    "osint": ["Watcher", "Scout", "Spectre", "Phantom"],
    "infra": ["Operator", "Mechanic", "Guardian", "Core"],
}

def generate_agent_name(specialty: str | None = None) -> str:
    """
    Generates a high-authority agent name using the CORTEX Naming Manifold.
    
    Example: Sovereign-Architect-Omega, Ghost-Scout-0XF
    """
    prefix = random.choice(PREFIXES)
    
    # Select core based on specialty or random
    if specialty and specialty.lower() in SPECIALTY_CORES:
        core = random.choice(SPECIALTY_CORES[specialty.lower()])
    else:
        core = random.choice(CORES)
    
    # Decide on suffix type: Traditional (Greek) or Hex/Code
    if random.random() > 0.4:
        suffix = random.choice(SUFFIXES)
    else:
        suffix = "".join(secrets.choice("0123456789ABCDEF") for _ in range(3))
        
    return f"{prefix}-{core}-{suffix}".lower()

if __name__ == "__main__":
    # Test generation
    for _ in range(5):
        print(generate_agent_name())
    for s in ["code", "security", "infra"]:
        print(f"{s:10s} -> {generate_agent_name(s)}")
