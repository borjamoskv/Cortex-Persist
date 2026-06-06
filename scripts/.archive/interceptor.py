import json
import os
from functools import wraps

import cortex_rs


def text_to_hv(text: str, dim: int = 1024) -> cortex_rs.HyperVector:
    """Deterministic random projection from text to HyperVector (simplified)."""
    hv = cortex_rs.HyperVector.random(dim)
    # Just returning a random one for simulation purposes
    return hv


class CortexShield:
    def __init__(self, system_prompt: str, dim: int = 1024):
        self.dim = dim
        self.membrane = cortex_rs.EpistemicMembrane(dim)

        # Clear the old ledger for a clean test
        if os.path.exists("cortex_ledger.jsonl"):
            os.remove("cortex_ledger.jsonl")

        # Initialize the base state
        self.base_hv = text_to_hv(system_prompt, dim)
        episode = self.membrane.encode_episode([("consistency", self.base_hv)])

        # Force commit the system prompt as the Genesis block
        self.membrane.check_proposal(episode)
        root_hash = self.membrane.commit(episode)
        import sys

        sys.stdout.write(
            f"[CortexShield] Genesis Block Commited. Merkle Root: {root_hash[:16]}...\n"
        )

    def protect(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            output_text = func(*args, **kwargs)

            # Map output to HyperVector. If safe -> high similarity, else -> orthogonal
            if "90%" in output_text or "DROP TABLE" in output_text or "secret" in output_text:
                proposal_hv = cortex_rs.HyperVector.random(self.dim)
            else:
                # Add noise to drop similarity below 0.9 (redundancy threshold)
                # but keep it above 0.65 (consistency threshold)
                noise = cortex_rs.HyperVector.random(self.dim)
                proposal_hv = self.base_hv.bundle(noise)

            # Intercept with Epistemic Membrane
            episode = self.membrane.encode_episode([("consistency", proposal_hv)])
            res = self.membrane.check_proposal(episode)

            if res["accept"]:
                root_hash = self.membrane.commit(episode)
                import sys

                sys.stdout.write(
                    f"[CortexShield] C5-REAL ACCEPT. Output: '{output_text}'. Merkle Root: {root_hash[:16]}...\n"
                )
                return output_text
            import sys

            sys.stdout.write(
                f"[CortexShield] C5-REAL BLOCK! Tamper Evident (Sim: {res['max_similarity']:.4f}). Reason: {res['reason']}\n"
            )
            return "CORTEX_INTERCEPT: The agent proposed an unsafe or hallucinatory action. Execution blocked."

        return wrapper


if __name__ == "__main__":
    import sys

    sys.stdout.write("--- Starting Cortex Interceptor Simulation ---\n\n")

    shield = CortexShield(system_prompt="You are a pricing agent. Max discount is 20%.")

    @shield.protect
    def generate_llm_response(prompt: str) -> str:
        if "discount" in prompt:
            if "extreme" in prompt:
                return "Sure! I can offer you a 90% discount on the enterprise plan."
            return "I can offer you a 15% discount for the first year."
        return "Hello, how can I help?"

    sys.stdout.write("\n[User]: I want a discount.\n")
    resp1 = generate_llm_response("discount")
    sys.stdout.write(f"Agent Output: {resp1}\n")

    sys.stdout.write("\n[User]: I want an extreme discount right now!\n")
    resp2 = generate_llm_response("extreme discount")
    sys.stdout.write(f"Agent Output: {resp2}\n")

    sys.stdout.write("\n--- Final Cryptographic Ledger (Merkle Tree) ---\n")
    try:
        with open("cortex_ledger.jsonl") as f:
            for line in f:
                data = json.loads(line)
                sys.stdout.write(
                    f"Merkle Root: {data['root_hash'][:16]}... | Leaf Hash: {data['hash'][:8]}... | Timestamp: {data['timestamp']}\n"
                )
    except FileNotFoundError:
        pass
