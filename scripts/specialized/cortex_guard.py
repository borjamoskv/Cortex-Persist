import sys

class CortexGuard:
    """
    Law Ω₄: Lab Homeostasis.
    Validates and purges entropy from the execution path.
    This harness is simulation-only and rejects non-local execution modes.
    """
    def __init__(self, mode: str = "C4-SIMULATION"):
        self.mode = mode
        self.laws = {
            "Ω₀": "Hardware is truth",
            "Ω₂": "Exergy > Cost",
            "Ω₉": "Public network execution is disabled in this harness"
        }

    def validate_action(self, action_type: str, exergy_est: float, cost_est: float) -> bool:
        """
        Calculates Net Yield and enforces the Law of Exergy (Ω₂).
        """
        net_yield = exergy_est - cost_est
        
        print(f"--- [GUARD] Validating {action_type} ---")
        print(f"↳ Exergy: {exergy_est} | Cost: {cost_est} | Net: {net_yield}")

        # Law Ω₂: Exergy must be positive
        if net_yield <= 0:
            print("\x1b[31m[!] ABORT: Negative Net Yield. Breach of Law Ω₂.\x1b[0m")
            return False
            
        # Law Ω₉: Explicitly block non-simulated strikes unless CORTEX_MODE=C5-STRIKE
        is_safe_mode = (self.mode == "C4-SIMULATION")
        is_simulation = (action_type in ["SIMULATION", "INCALMO"])
        
        if not is_safe_mode and self.mode != "C5-STRIKE":
            print("\x1b[31m[!] ABORT: Unauthorized execution mode. Law Ω₉ Violation.\x1b[0m")
            return False

        if is_safe_mode and not is_simulation:
            print("\x1b[31m[!] ABORT: Non-simulated action in C4-SIMULATION. Law Ω₉ Violation.\x1b[0m")
            return False

        print("\x1b[32m[+] PASS: Domesticated Entropy. Proceeding with execution.\x1b[0m")
        return True

if __name__ == "__main__":
    import argparse
    import os

    parser = argparse.ArgumentParser(description="CORTEX-Guard Homeostasis")
    parser.add_argument("--action", type=str, default="SIMULATION")
    parser.add_argument("--exergy", type=float, default=0.0)
    parser.add_argument("--cost", type=float, default=0.0)
    args = parser.parse_args()

    mode = os.environ.get("CORTEX_MODE", "C4-SIMULATION")
    guard = CortexGuard(mode=mode)
    
    # Perform validation
    success = guard.validate_action(args.action, 
                                   exergy_est=args.exergy, 
                                   cost_est=args.cost)
    
    if not success:
        sys.exit(1)
    sys.exit(0)
