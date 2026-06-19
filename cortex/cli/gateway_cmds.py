# [C5-REAL] Exergy-Maximized

from __future__ import annotations

import json
import subprocess
import os

import click
from rich.panel import Panel
from rich.table import Table

from cortex.cli.common import DEFAULT_DB, cli, console, get_engine
from cortex.engine.entropy_core import EntropyCore
from cortex.guards.entropy_guard import EntropyGuardEngine, GuardAction
from cortex.engine.decision_engine import DecisionEngine


@click.group("gateway")
def gateway_cmds() -> None:
    """CORTEX gateway management commands."""


@gateway_cmds.command("health")
@click.option("--db", default=DEFAULT_DB, help="Database path")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def health(db: str, as_json: bool) -> None:
    """Check gateway resonance and health."""
    # For now, it mirrors global health or specific gateway metrics if available
    from cortex.extensions.health import HealthCollector, HealthScorer

    engine = get_engine(db)
    collector = HealthCollector(db_path=db)
    metrics = collector.collect_all()
    hs = HealthScorer.score(metrics)

    if as_json:
        out = {
            "status": "healthy" if hs.score > 80 else "degraded",
            "score": hs.score,
            "grade": hs.grade.letter,
            "timestamp": hs.timestamp,
        }
        click.echo(json.dumps(out, indent=2))
        return

    console.print(
        f"\n[[noir.cyber]⚡[/]] Gateway Health: [bold]{hs.score:.1f}/100[/] ([noir.yinmn]{hs.grade.letter}[/])"
    )
    console.print(f"[dim]State: {'Resonant' if hs.score > 90 else 'Stable'}[/]\n")
    engine.close_sync()


cli.add_command(gateway_cmds)

@gateway_cmds.command("audit")
@click.option("--pr-id", required=True, help="Pull Request ID")
@click.option("--tenant", default="acme_corp", help="Tenant ID")
@click.option("--additions", type=int, default=None, help="Explicit additions override")
@click.option("--deletions", type=int, default=None, help="Explicit deletions override")
@click.option("--files-changed", type=int, default=None, help="Explicit files changed override")
@click.option("--commits", type=int, default=None, help="Explicit commit count override")
@click.option("--includes-tests", type=bool, is_flag=True, default=False, help="Flag if PR includes tests")
@click.option("--target-branch", default="origin/main", help="Git branch to diff against if auto-detecting")
@click.option("--db", default="/tmp/cortex_gateway.db", help="Database path (ephemeral by default)")
def audit(pr_id: str, tenant: str, additions: int | None, deletions: int | None, files_changed: int | None, commits: int | None, includes_tests: bool, target_branch: str, db: str) -> None:
    """Audits an AI-generated Pull Request for entropy and issues a cryptographic seal."""
    import asyncio
    import aiosqlite
    from cortex.audit.ledger import EnterpriseAuditLedger
    from cortex.auth.enterprise_identity import SovereignIdentity
    from cortex.guards.enterprise_guard import EnterpriseRBACGuard
    from cortex.gateway.code_governance import CodeGovernanceGateway

    workspace_root = os.getcwd()
    
    # 1. HYBRID DIFF PARSING
    auto_add = 0
    auto_del = 0
    auto_files = 0
    auto_commits = 1
    
    try:
        if additions is None or deletions is None or files_changed is None:
            cmd = ["git", "diff", "--numstat", target_branch]
            out = subprocess.check_output(cmd, cwd=workspace_root, text=True, stderr=subprocess.DEVNULL)
            lines = out.strip().split("\n")
            auto_files = len([l for l in lines if l.strip()])
            for line in lines:
                parts = line.split()
                if len(parts) >= 2:
                    auto_add += int(parts[0]) if parts[0].isdigit() else 0
                    auto_del += int(parts[1]) if parts[1].isdigit() else 0
                    
        if commits is None:
            c_cmd = ["git", "rev-list", "--count", f"{target_branch}..HEAD"]
            c_out = subprocess.check_output(c_cmd, cwd=workspace_root, text=True, stderr=subprocess.DEVNULL)
            auto_commits = int(c_out.strip())
    except Exception:
        # Fallback silently if git history is detached or shallow
        pass
        
    payload = {
        "additions": additions if additions is not None else auto_add,
        "deletions": deletions if deletions is not None else auto_del,
        "files_changed": files_changed if files_changed is not None else auto_files,
        "commits": commits if commits is not None else auto_commits,
        "includes_tests": includes_tests
    }
    
    async def run_audit():
        async with aiosqlite.connect(db) as conn:
            ledger = EnterpriseAuditLedger(conn)
            await ledger.ensure_table()
            rbac = EnterpriseRBACGuard()
            gateway = CodeGovernanceGateway(ledger=ledger, rbac_guard=rbac)
            
            identity = SovereignIdentity(tenant_id=tenant, actor_id="ci_runner", role="CI_GATEWAY")
            
            return await gateway.evaluate_pull_request(identity, pr_id, payload)
            
    result = asyncio.run(run_audit())
    
    # 2. MARKDOWN GENERATION
    md = [
        f"## 🧯 CORTEX CI/CD Firewall Report",
        f"**PR ID:** `{result['pr_id']}` | **Status:** `{'✅ APPROVED' if result['status'] == 'APPROVED' else '❌ REJECTED'}`",
        f"**Entropy Score:** `{result['risk_profile']['score']} ({result['risk_profile']['level']})`",
        f"",
        f"### Cryptographic Audit Seal",
        f"```",
        f"SHA-256: {result['audit_proof']}",
        f"```",
        f"",
        f"### Risk Diagnostics"
    ]
    
    if result["risk_profile"]["reasons"]:
        for reason in result["risk_profile"]["reasons"]:
            md.append(f"- ⚠️ {reason}")
    else:
        md.append("- 🟢 No critical risk vectors detected.")
        
    md.extend([
        f"",
        f"### CHRONOS-1 ROI Receipt",
        f"- **Autonomous Audit Saved:** {result['roi_receipt']['hours_saved']} human hours.",
        f"- **Equivalent Dollar Value:** ${result['roi_receipt']['money_saved']:.2f} USD.",
        f"- **Stats:** Mutated {result['roi_receipt']['file_count']} files across {result['roi_receipt']['git_commits']} commits."
    ])
    
    markdown_output = "\n".join(md)
    click.echo(markdown_output)
    
    # 3. REJECTION BEHAVIOR
    if result["status"] == "REJECTED":
        exit(1)
    exit(0)
