import json
import os
import yaml
import re

class BountyGuard:
    """
    CORTEX-PERSIST: Bounty Policy Enforcement Layer.
    Ensures all extraction targets are defensible and in-scope.
    """
    def __init__(self, config_path="config.yaml"):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        self.policies_dir = self.config.get("policies", {}).get("dir", "data/policies")
        self.enforce = self.config.get("policies", {}).get("enforce_compliance", True)
        self.active_guards = {}
        self._load_active_policies()

    def _load_active_policies(self):
        if not os.path.exists(self.policies_dir):
            return
        for f in os.listdir(self.policies_dir):
            if f.endswith(".json") and not f.endswith(".compiled.json"):
                # In production, we'd use the compiled version if available
                p_path = os.path.join(self.policies_dir, f)
                with open(p_path, 'r') as pf:
                    try:
                        policy = json.load(pf)
                        if "program_id" in policy:
                            self.active_guards[policy["program_id"]] = policy
                    except Exception:
                        continue

    def validate_target(self, url):
        """
        Returns (is_allowed: bool, reason: str, policy_id: str)
        """
        if not self.enforce:
            return True, "Enforcement disabled", "NONE"

        # Match URL against active policies
        for pid, policy in self.active_guards.items():
            for allowed in policy["scope"]["in_scope"]:
                # Simple wildcard matching for now
                pattern = allowed["target"].replace(".", "\\.").replace("*", ".*")
                if re.search(pattern, url):
                    # Found a policy match, check against out-of-scope
                    for blocked in policy["scope"].get("out_of_scope", []):
                        blocked_pattern = blocked.replace(".", "\\.").replace("*", ".*")
                        if re.search(blocked_pattern, url):
                            return False, f"Target '{url}' explicitly out-of-scope for {pid}", pid
                    return True, "Target in scope", pid
        
        return False, f"No matching policy found for target '{url}'", "NONE"

if __name__ == "__main__":
    guard = BountyGuard()
    # Test Firedancer
    test_url = "https://github.com/firedancer-io/firedancer/src/main.c"
    allowed, reason, pid = guard.validate_target(test_url)
    print(f"Target: {test_url} | Allowed: {allowed} | Reason: {reason} | Policy: {pid}")

    # Test out-of-scope
    test_url_2 = "https://api.firedancer.io/v1/meta"
    allowed2, reason2, pid2 = guard.validate_target(test_url_2)
    print(f"Target: {test_url_2} | Allowed: {allowed2} | Reason: {reason2} | Policy: {pid2}")
