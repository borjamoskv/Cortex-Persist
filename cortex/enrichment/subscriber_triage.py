"""
[C5-REAL] Exergy-Maximized Subscriber Triage Engine
Transforms high-entropy subscriber strings into deterministic PPI vectors.
"""

import hashlib
import re
from datetime import datetime

# Heuristic Constants
V1_ROLE_BASED_REGEX = re.compile(
    r"^(info|demos|submissions|press|news|editorial|team|sales|hello|contact|wholesale|volunteers|backme|music|detection-inquiries|nao-inquiries|benchmarks|ensdomainscollector|geral|general|admin)@",
    re.IGNORECASE,
)

V2_HIGH_PROFILE_DOMAINS = {
    "amazon.com",
    "coinbase.com",
    "nvidia.com",
    "shopify.com",
    "foundersfund.com",
    "socialcapital.com",
    "microstrategy.com",
    "inflection.ai",
    "openai.com",
    "ssi.inc",
    "iohk.io",
    "adobe.com",
    "near.org",
    "huggingface.co",
}

V3_ACADEMIC_DOMAINS = {
    "csic.es",
    "ugr.es",
    "upv.es",
    "us.es",
    "ual.es",
    "upc.edu",
    "uva.es",
    "stanford.edu",
    "dair-institute.org",
    "cuny.edu",
}

V4_WEB3_DOMAINS = {
    "blocknative.com",
    "wintermute.com",
    "nunet.io",
    "starkware.co",
    "bittensor.com",
    "dydx.exchange",
    "lagrange.dev",
    "spheron.network",
    "myshell.ai",
    "gsr.io",
    "maven11.com",
    "pyth.network",
    "morpheus.network",
    "herodotus.dev",
    "axiom.xyz",
    "drift.trade",
    "aethir.com",
    "singularitynet.io",
    "helium.com",
    "phala.network",
    "nillion.com",
    "jup.ag",
    "ankr.com",
    "sentient.foundation",
    "succinct.xyz",
    "dealflow.es",
}


def generate_taint(payload: str) -> str:
    """Generate CORTEX-TAINT for structural integrity."""
    timestamp = datetime.utcnow().isoformat()
    hash_payload = hashlib.sha3_256(payload.encode()).hexdigest()
    return f"taint:MOSKV-1:enrichment:{timestamp}:{hash_payload}"


def _match_domain_or_parent(domain: str, domain_set: set) -> bool:
    """Check if domain or any of its parent domains is in the set."""
    if domain in domain_set:
        return True
    parts = domain.split(".")
    for i in range(1, len(parts) - 1):
        parent = ".".join(parts[i:])
        if parent in domain_set:
            return True
    return False


def triage_subscriber(email: str) -> tuple[str, int, str]:
    """
    Evaluates an email and returns (Vector_Class, Reality_PPI, Reason)
    """
    email_lower = email.lower().strip()
    if not email_lower or "@" not in email_lower:
        return ("V0_INVALID", 0, "Malformed string")

    local_part, domain = email_lower.split("@", 1)

    # [V-1] Sinkholes / Role-Based
    if V1_ROLE_BASED_REGEX.match(email_lower):
        return ("V1_ROLE_BASED", 1, "Role-based CRM/Sinkhole")

    # [V-2] Executive Assistants
    if _match_domain_or_parent(domain, V2_HIGH_PROFILE_DOMAINS):
        return ("V2_HIGH_PROFILE", 1, "High-profile domain (EA Filtered)")

    # [V-3] Academic SEG Filters
    if _match_domain_or_parent(domain, V3_ACADEMIC_DOMAINS) or domain.endswith(".edu") or domain.endswith(".ac.uk"):
        return ("V3_ACADEMIC", 3, "Academic SEG Firewall")

    # [V-4] Web3/VC Noise
    if (
        _match_domain_or_parent(domain, V4_WEB3_DOMAINS)
        or domain.endswith(".exchange")
        or domain.endswith(".network")
        or domain.endswith(".xyz")
    ):
        return ("V4_WEB3_VC", 3, "Web3/VC High Noise Inbox")

    # [V-5] Organic C5-REAL
    return ("V5_ORGANIC", 5, "Personal/Direct Attention")


def process_batch(emails: list[str]) -> dict[str, dict]:
    """Process a list of emails into a deterministic mapping."""
    results = {}
    for email in emails:
        vector, ppi, reason = triage_subscriber(email)
        taint = generate_taint(email + vector)
        results[email] = {
            "vector": vector,
            "ppi_reality": ppi,
            "reason": reason,
            "signature": taint,
        }
    return results


if __name__ == "__main__":
    # Test collapse
    test_set = [
        "demos@ninjatune.net",
        "borja@borjamoskv.com",
        "jeff@amazon.com",
        "sierra@iiia.csic.es",
        "Matt@blocknative.com",
    ]
    matrix = process_batch(test_set)
    for k, v in matrix.items():
        print(f"{k} -> {v['vector']} [PPI:{v['ppi_reality']}]")
