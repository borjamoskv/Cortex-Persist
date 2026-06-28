"""
[C5-REAL] CORTEX APEX Agentic Benchmark Protocol Evaluator.
Reverse-engineered evaluation matrix for Frontier Models.
Protocol: A-EVAL-2026.

*** ULTRATHINK P0 OVERRIDE: ASYNCHRONOUS LEDGER INTEGRATION ***
This module evaluates agentic causal trajectories to extract thermodynamic exergy 
(Net Improvement, Steerability, Bash Recovery, Tool Hallucination) and cryptographically
anchors the result to the Master Ledger.
"""

import argparse
import asyncio
import csv
import json
import logging
import subprocess
from pathlib import Path
from typing import Optional

import aiosqlite

from cortex.audit.ledger import EnterpriseAuditLedger

logger = logging.getLogger("cortex.benchmark.agentic_eval")
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    logger.setLevel(logging.INFO)

class AgenticMetrics:
    def __init__(self):
        self.total_sessions: int = 0
        self.total_cycles: int = 0
        self.net_improvement_commits: int = 0
        self.reverted_commits: int = 0
        self.zero_intervention_successes: int = 0
        self.praise_count: int = 0
        self.complaint_count: int = 0
        self.corrections: int = 0
        self.successful_corrections: int = 0
        self.bash_errors: int = 0
        self.bash_recoveries: int = 0
        self.tool_hallucinations: int = 0
        self.total_tool_calls: int = 0

class AsyncAgenticEvaluator:
    def __init__(self, transcripts_dir: Path, db_path: str = "cortex_ledger.db"):
        self.transcripts_dir = transcripts_dir
        self.db_path = db_path
        self.metrics = AgenticMetrics()
        self.session_scores: list[dict[str, float]] = []

    def _get_git_net_improvement(self) -> float:
        """[C5-REAL] Extract empirical Exergy Delta from the repository graph."""
        try:
            # Count total commits vs commits containing 'revert' or 'fix'
            total_cmd = subprocess.run(
                ["git", "rev-list", "--count", "HEAD"], 
                capture_output=True, text=True, check=True
            )
            total_commits = int(total_cmd.stdout.strip() or 1)

            revert_cmd = subprocess.run(
                ["git", "log", "--oneline", "--grep=revert", "--grep=fix", "-i"], 
                capture_output=True, text=True, check=True
            )
            revert_commits = len([line for line in revert_cmd.stdout.splitlines() if line])

            # Net Improvement = ratio of exergy-positive structural mutations
            return ((total_commits - revert_commits) / total_commits) * 100
        except Exception as e:
            logger.warning(f"Failed to compute empirical Git exergy: {e}")
            return 0.0

    async def evaluate_session(self, transcript_path: Path, ledger: EnterpriseAuditLedger) -> None:
        """Processes a single transcript.jsonl file and anchors validation to Ledger."""
        self.metrics.total_sessions += 1
        
        try:
            with open(transcript_path, encoding='utf-8') as f:
                lines = f.readlines()
        except FileNotFoundError:
            logger.error(f"Transcript not found: {transcript_path}")
            return

        session_events = [json.loads(line) for line in lines if line.strip()]
        
        user_msgs = 0
        error_count = 0
        praise_found = False
        complaint_found = False
        last_bash_error = False
        
        local_tool_calls = 0
        local_hallucinations = 0
        local_bash_errors = 0
        local_recoveries = 0

        for event in session_events:
            step_type = event.get("type", "")
            content = event.get("content", "").lower()
            
            if step_type == "USER_INPUT":
                user_msgs += 1
                if any(p in content for p in ["looks good", "perfect", "thanks", "great", "awesome", "funciona"]):
                    praise_found = True
                if any(c in content for c in ["no", "instead", "change this", "wrong", "fail", "error", "bad"]):
                    complaint_found = True
                    self.metrics.corrections += 1
            
            if step_type == "PLANNER_RESPONSE":
                self.metrics.total_cycles += 1
                tool_calls = event.get("tool_calls", [])
                for tc in tool_calls:
                    self.metrics.total_tool_calls += 1
                    local_tool_calls += 1
                    tc_str = str(tc).lower()
                    if "error" in tc_str or "invalid" in tc_str or "unknown" in tc_str:
                        self.metrics.tool_hallucinations += 1
                        local_hallucinations += 1
                        
            if step_type == "TOOL_RESPONSE":
                output = event.get("output", "")
                if "exit code" in output and "exit code 0" not in output:
                    self.metrics.bash_errors += 1
                    local_bash_errors += 1
                    last_bash_error = True
                elif last_bash_error and ("exit code 0" in output or "success" in output.lower()):
                    self.metrics.bash_recoveries += 1
                    local_recoveries += 1
                    last_bash_error = False
                    
            if step_type == "ERROR":
                error_count += 1
                
        if user_msgs == 1 and error_count == 0:
            self.metrics.zero_intervention_successes += 1
            
        if praise_found:
            self.metrics.praise_count += 1
        if complaint_found:
            self.metrics.complaint_count += 1

        hallucination_rate = (local_hallucinations / local_tool_calls) if local_tool_calls else 0.0
        
        # [C5-REAL] Cryptographic Anchoring
        await ledger.log_action(
            tenant_id="global",
            actor_role="system",
            actor_id="evaluator_omega",
            action="EVAL_SESSION_COMPUTED",
            resource=str(transcript_path),
            status=f"Hallucination:{hallucination_rate:.2f}"
        )

    async def compute_aggregate_metrics(self) -> dict[str, str]:
        """Calculates final percentages akin to the A-EVAL-2026 leaderboard."""
        ts = self.metrics.total_sessions or 1
        tt = self.metrics.total_tool_calls or 1
        be = self.metrics.bash_errors or 1
        co = self.metrics.corrections or 1
        
        net_improvement = self._get_git_net_improvement()
        
        return {
            "Rank": "N/A",
            "Model": "Local-Swarm-ULTRATHINK",
            "Net Improvement": f"{net_improvement:.2f}%",
            "Confirmed Success": f"{(self.metrics.zero_intervention_successes / ts) * 100:.2f}%",
            "Praise vs Complaint": f"{(self.metrics.praise_count / ts) * 100:.2f}% / {(self.metrics.complaint_count / ts) * 100:.2f}%",
            "Steerability": f"{(self.metrics.successful_corrections / co) * 100:.2f}%",
            "Bash Recovery": f"{(self.metrics.bash_recoveries / be) * 100:.2f}%",
            "Tool Hallucination": f"{(self.metrics.tool_hallucinations / tt) * 100:.2f}%",
            "Sessions": str(self.metrics.total_sessions)
        }

    async def run_all(self, csv_export: Optional[str] = None) -> dict[str, str]:
        logger.info(f"Scanning directory: {self.transcripts_dir} for transcript.jsonl files...")
        paths = list(self.transcripts_dir.rglob("transcript.jsonl"))
        
        async with aiosqlite.connect(self.db_path) as conn:
            ledger = EnterpriseAuditLedger(conn)
            await ledger.ensure_table()
            
            if not paths:
                logger.warning("No transcript.jsonl files found.")
            else:
                for path in paths:
                    await self.evaluate_session(path, ledger)
            
            results = await self.compute_aggregate_metrics()
            
            if csv_export:
                self._export_csv(csv_export, results)
                
            await ledger.log_action(
                tenant_id="global",
                actor_role="system",
                actor_id="evaluator_omega",
                action="GLOBAL_MATRIX_GENERATED",
                resource="A-EVAL-2026"
            )
            await ledger.close()
            
        return results

    def _export_csv(self, csv_path: str, results: dict[str, str]) -> None:
        try:
            with open(csv_path, "w", newline="") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(list(results.keys()))
                writer.writerow(list(results.values()))
            logger.info(f"[C5-REAL] Structural Matrix exported to {csv_path}")
        except Exception as e:
            logger.error(f"CSV export failed: {e}")

async def main_async() -> None:
    parser = argparse.ArgumentParser(description="META_EVAL_AGENTIC task-level benchmark (C5-REAL P0)")
    parser.add_argument("-d", "--directory", type=str, required=True, help="Directory containing brain/session logs")
    parser.add_argument("-o", "--output", type=str, default="a_eval_results.csv", help="CSV export path")
    parser.add_argument("--db", type=str, default="cortex_ledger.db", help="SQLite Audit Ledger Database")
    args = parser.parse_args()

    evaluator = AsyncAgenticEvaluator(Path(args.directory), db_path=args.db)
    results = await evaluator.run_all(csv_export=args.output)
    
    print("\n=== A-EVAL-2026 CORTEX BENCHMARK RESULTS (ULTRATHINK P0) ===")
    print("-" * 65)
    for k, v in results.items():
        print(f"  {k:<20}: {v}")
    print("-" * 65)

def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
