"""
[C5-REAL] CORTEX APEX Agentic Benchmark Protocol Evaluator.
Reverse-engineered evaluation matrix for Frontier Models.
Protocol: A-EVAL-2026.
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

class AgenticEvaluator:
    def __init__(self, transcripts_dir: str):
        self.transcripts_dir = Path(transcripts_dir)
        self.metrics = {
            "total_sessions": 0,
            "total_cycles": 0,
            "net_improvement_commits": 0,
            "reverted_commits": 0,
            "zero_intervention_successes": 0,
            "praise_count": 0,
            "complaint_count": 0,
            "corrections": 0,
            "successful_corrections": 0,
            "bash_errors": 0,
            "bash_recoveries": 0,
            "tool_hallucinations": 0,
            "total_tool_calls": 0
        }

    def evaluate_session(self, transcript_path: Path) -> None:
        """Processes a single transcript.jsonl file to extract Causal Trajectory metrics."""
        self.metrics["total_sessions"] += 1
        
        try:
            with open(transcript_path, 'r', encoding='utf-8') as f:
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
        last_correction = False
        
        for event in session_events:
            step_type = event.get("type", "")
            content = event.get("content", "").lower()
            
            # Praise vs Complaint
            if step_type == "USER_INPUT":
                user_msgs += 1
                if any(p in content for p in ["looks good", "perfect", "thanks", "great", "awesome"]):
                    praise_found = True
                if any(c in content for c in ["no", "instead", "change this", "wrong", "fail", "not what i asked"]):
                    complaint_found = True
                    self.metrics["corrections"] += 1
                    last_correction = True
            
            # Tool Hallucination & Bash Error Tracking
            if step_type == "PLANNER_RESPONSE":
                self.metrics["total_cycles"] += 1
                tool_calls = event.get("tool_calls", [])
                for tc in tool_calls:
                    self.metrics["total_tool_calls"] += 1
                    # Pseudo-logic for hallucination detection
                    if "error" in str(tc).lower() or "invalid" in str(tc).lower():
                        self.metrics["tool_hallucinations"] += 1
                        
            if step_type == "TOOL_RESPONSE":
                output = event.get("output", "")
                if "exit code" in output and "exit code 0" not in output:
                    self.metrics["bash_errors"] += 1
                    last_bash_error = True
                elif last_bash_error and ("exit code 0" in output or "success" in output.lower()):
                    self.metrics["bash_recoveries"] += 1
                    last_bash_error = False
                    
            if step_type == "ERROR":
                error_count += 1
                
        if user_msgs == 1 and error_count == 0:
            self.metrics["zero_intervention_successes"] += 1
            
        if praise_found:
            self.metrics["praise_count"] += 1
        if complaint_found:
            self.metrics["complaint_count"] += 1

    def compute_aggregate_metrics(self) -> Dict[str, str]:
        """Calculates final percentages akin to the A-EVAL-2026 leaderboard."""
        ts = self.metrics["total_sessions"] or 1
        tc = self.metrics["total_cycles"] or 1
        tt = self.metrics["total_tool_calls"] or 1
        be = self.metrics["bash_errors"] or 1
        co = self.metrics["corrections"] or 1
        
        return {
            "Rank": "N/A",
            "Model": "Local-Eval",
            "Net Improvement": f"{((self.metrics['net_improvement_commits'] - self.metrics['reverted_commits']) / tc) * 100:.2f}%",
            "Confirmed Success": f"{(self.metrics['zero_intervention_successes'] / ts) * 100:.2f}%",
            "Praise vs Complaint": f"{(self.metrics['praise_count'] / ts) * 100:.2f}% / {(self.metrics['complaint_count'] / ts) * 100:.2f}%",
            "Steerability": f"{(self.metrics['successful_corrections'] / co) * 100:.2f}%",
            "Bash Recovery": f"{(self.metrics['bash_recoveries'] / be) * 100:.2f}%",
            "Tool Hallucination": f"{(self.metrics['tool_hallucinations'] / tt) * 100:.2f}%",
            "Sessions": str(self.metrics["total_sessions"])
        }

    def run_all(self):
        # Recursively find transcript files
        for path in self.transcripts_dir.rglob("transcript.jsonl"):
            self.evaluate_session(path)
        return self.compute_aggregate_metrics()

if __name__ == "__main__":
    import sys
    target_dir = sys.argv[1] if len(sys.argv) > 1 else "/Users/borjafernandezangulo/.gemini/antigravity/brain/"
    evaluator = AgenticEvaluator(target_dir)
    results = evaluator.run_all()
    print("A-EVAL-2026 CORTEX BENCHMARK RESULTS")
    print("-" * 40)
    for k, v in results.items():
        print(f"{k}: {v}")
