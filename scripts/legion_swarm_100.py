#!/usr/bin/env python3
"""LEGION-Ω 100-Agent Remediation Swarm — Standalone Entry Point.

Usage:
    python scripts/legion_swarm_100.py --db ~/.cortex/cortex.db --dry-run
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from cortex.extensions.swarm.remediation.engine import LegionRemediationEngine


async def main():
    parser = argparse.ArgumentParser(description="LEGION-Ω 100-Agent Remediation Swarm")
    parser.add_argument("--db", default="~/.cortex/cortex.db", help="Database path")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    parser.add_argument("--report", help="Path to save JSON report")
    args = parser.parse_args()

    db_path = str(Path(args.db).expanduser())
    if not Path(db_path).exists():
        print(f"Error: Database not found at {db_path}")
        sys.exit(1)

    engine = LegionRemediationEngine(db_path, dry_run=args.dry_run)
    
    print("--- LEGION-Ω REMEDIATION SWARM ---")
    print(f"DB: {db_path}")
    print(f"Dry Run: {args.dry_run}")
    print("Initializing 100-agent mesh...")

    report = await engine.execute()

    print("\n--- Results ---")
    print(f"Facts Scanned: {report.total_facts_scanned}")
    print(f"Issues Found:  {report.total_issues_found}")
    print(f"Fixes Passed:  {report.fixes_applied}")
    print(f"Fixes Rejected: {report.fixes_rejected}")
    print(f"Fixes Failed:   {report.fixes_failed}")

    if args.report:
        engine.save_report(report, args.report)
        print(f"Report saved to {args.report}")

if __name__ == "__main__":
    asyncio.run(main())
