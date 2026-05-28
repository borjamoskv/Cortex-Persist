import os
import sys
import json
import subprocess
import datetime
from typing import Dict, Any

class OuroborosIncalmo:
    """
    Sovereign Attack Abstraction Layer (Incalmo-style).
    Law Ω₅: Zero-Rhetoric Mandate.
    """
    def __init__(self, root_dir: str):
        self.root_dir = root_dir
        self.primitives_path = os.path.join(root_dir, "memory", "primitives.json")
        self.reports_dir = os.path.join(root_dir, "reports")
        self.guard_path = os.path.join(root_dir, "cortex_guard.py")
        
        with open(self.primitives_path, "r") as f:
            self.spec = json.load(f)

    def run_intent(self, intent_name: str, cost: float = 0.1) -> Dict[str, Any]:
        """
        Executes a declarative security intent.
        """
        if intent_name not in self.spec["intents"]:
            raise ValueError(f"Unknown intent: {intent_name}")
            
        intent = self.spec["intents"][intent_name]
        exergy = intent["exergy_weight"]
        
        # Phase 1: Homeostasis Validation
        print(f"[*] Validating Homeostasis for {intent_name}...")
        guard_cmd = [
            "python3", self.guard_path,
            "--action", "INCALMO",
            "--exergy", str(exergy),
            "--cost", str(cost)
        ]
        
        try:
            subprocess.run(guard_cmd, check=True)
        except subprocess.CalledProcessError:
            print("[!] Homeostasis Failure. ABORTING.")
            return {"status": "FAILED_GUARD", "intent": intent_name}

        # Phase 2: Forge Execution
        print(f"[*] Executing Forge Primitive: {intent['forge_filter']}...")
        forge_cmd = [
            "forge", "test",
            "--match-test", intent["forge_filter"],
            "-vvvv"
        ]
        
        process = subprocess.Popen(
            forge_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=self.root_dir
        )
        stdout, stderr = process.communicate()
        success = (process.returncode == 0)
        
        # Phase 3: Telemetry Crystallization
        report = {
            "intent": intent_name,
            "timestamp": datetime.datetime.now().isoformat(),
            "status": "C5-REAL_SUCCESS" if success else "STRIKE_FAILED",
            "forge_output": stdout[-2000:], # Last 2k chars
            "error": stderr if not success else None
        }
        
        self._persist_report(report)
        return report

    def _persist_report(self, report: Dict[str, Any]):
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"incalmo_strike_{report['intent']}_{timestamp}.json"
        filepath = os.path.join(self.reports_dir, filename)
        
        with open(filepath, "w") as f:
            json.dump(report, f, indent=2)
        print(f"[+] Strike Persisted: {filepath}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Ouroboros-Incalmo Engine")
    parser.add_argument("--intent", type=str, required=True, help="Security Intent to execute")
    parser.add_argument("--cost", type=float, default=0.1, help="Estimated compute cost")
    args = parser.parse_args()

    # Determine root dir (current directory)
    root = os.getcwd()
    engine = OuroborosIncalmo(root)
    
    result = engine.run_intent(args.intent, cost=args.cost)
    if result["status"] == "C5-REAL_SUCCESS":
        print("\x1b[32m[Ω] STRIKE SUCCESSFUL. State extracted.\x1b[0m")
        sys.exit(0)
    else:
        print(f"\x1b[31m[!] STRIKE FAILED: {result['status']}\x1b[0m")
        sys.exit(1)
