import asyncio
import aiosqlite
import os
import json

from cortex.audit.ledger import EnterpriseAuditLedger
from cortex.auth.enterprise_identity import SovereignIdentity
from cortex.guards.enterprise_guard import EnterpriseRBACGuard
from cortex.gateway.code_governance import CodeGovernanceGateway

async def simulate_github_action():
    db_path = "/tmp/cortex_gateway.db"
    if os.path.exists(db_path):
        os.remove(db_path)
        
    async with aiosqlite.connect(db_path) as conn:
        ledger = EnterpriseAuditLedger(conn)
        rbac = EnterpriseRBACGuard()
        
        # Instantiate the Gateway
        gateway = CodeGovernanceGateway(ledger=ledger, rbac_guard=rbac)
        
        # Identity of the CI/CD Pipeline (GitHub Actions)
        ci_identity = SovereignIdentity(
            tenant_id="acme_corp",
            actor_id="github_actions_bot",
            role="CI_GATEWAY"
        )
        
        # Mock Payload 1: Safe PR
        safe_pr = {
            "files_changed": 3,
            "additions": 45,
            "deletions": 10,
            "commits": 2,
            "includes_tests": True
        }
        
        print("\n--- Evaluating SAFE PR ---")
        result_safe = await gateway.evaluate_pull_request(ci_identity, "pr-101", safe_pr)
        print(json.dumps(result_safe, indent=2))
        assert result_safe["status"] == "APPROVED"
        
        # Mock Payload 2: Risky PR
        risky_pr = {
            "files_changed": 18,
            "additions": 1500,
            "deletions": 200,
            "commits": 1,
            "includes_tests": False
        }
        
        print("\n--- Evaluating RISKY PR ---")
        result_risky = await gateway.evaluate_pull_request(ci_identity, "pr-102", risky_pr)
        print(json.dumps(result_risky, indent=2))
        assert result_risky["status"] == "REJECTED"

if __name__ == "__main__":
    asyncio.run(simulate_github_action())
