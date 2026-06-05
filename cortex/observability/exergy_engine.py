import os
import json
import statistics
import math
import re
from datetime import datetime
from typing import List, Dict, Any, Tuple

CRONOS_LOG = os.path.expanduser("~/.gemini/config/skills/_metrics/cronos_memory.jsonl")
WORKFLOWS_DIR = os.path.expanduser("~/.agents/workflows")

class ExergyEngine:
    """
    Core engine for CORTEX Adaptive Runtime.
    Implements Nivel 2 (Entropy Drift) to Nivel 6 (Counterfactual Ledger).
    """
    def __init__(self):
        self.history = self._load_cronos_history()
        self.genomes = self._extract_workflow_genomes()

    def _load_cronos_history(self) -> List[Dict[str, Any]]:
        records = []
        if os.path.exists(CRONOS_LOG):
            with open(CRONOS_LOG, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        records.append(json.loads(line))
        return records

    def _extract_workflow_genomes(self) -> Dict[str, List[str]]:
        """Extracts 'genes' (tools, keywords, paradigms) from workflows."""
        genomes = {}
        if not os.path.exists(WORKFLOWS_DIR):
            return genomes
            
        for file in os.listdir(WORKFLOWS_DIR):
            if not file.endswith(".md"):
                continue
            wf_name = file.replace(".md", "")
            genes = set()
            with open(os.path.join(WORKFLOWS_DIR, file), 'r', encoding='utf-8') as f:
                content = f.read().lower()
                
                # Gene extraction heuristics
                if "python" in content or "script" in content: genes.add("python")
                if "sql" in content or "database" in content or "sqlite" in content: genes.add("sql")
                if "mcp" in content: genes.add("mcp")
                if "search" in content or "brave" in content: genes.add("search")
                if "browser" in content or "scraping" in content: genes.add("browser")
                if "github" in content or "pr" in content: genes.add("github")
                if "visual" in content or "ui" in content or "css" in content: genes.add("frontend")
                if "plan" in content or "architecture" in content: genes.add("planning")
                
            genomes[wf_name] = list(genes)
        return genomes

    def get_entropy_drift(self, workflow: str) -> Dict[str, Any]:
        """Nivel 2: Detects entropy drift based on recent exergy vs historical."""
        wf_history = [r for r in self.history if r.get('workflow') == workflow]
        if len(wf_history) < 3:
            return {"status": "INSUFFICIENT_DATA"}
            
        scores = [r.get('exergy_score', 0) for r in wf_history]
        recent = scores[-1]
        baseline = scores[:-1]
        
        avg = statistics.mean(baseline)
        std = statistics.stdev(baseline) if len(baseline) > 1 else 0
        
        deviation_pct = ((recent - avg) / avg) * 100 if avg > 0 else 0
        
        # If recent is > 1.5 standard deviations below the mean, it's degraded
        status = "NOMINAL"
        if std > 0 and recent < avg - (1.5 * std):
            status = "DEGRADED"
        elif deviation_pct < -30:
            status = "DEGRADED"
            
        return {
            "workflow": workflow,
            "expected_exergy": round(avg, 4),
            "actual_exergy": round(recent, 4),
            "deviation_pct": round(deviation_pct, 1),
            "status": status
        }

    def predict(self, workflow: str) -> Dict[str, float]:
        """Nivel 3: Prediction Engine for runtime and exergy."""
        wf_history = [r for r in self.history if r.get('workflow') == workflow]
        if not wf_history:
            return {"predicted_runtime": 15.0, "predicted_outcome": 1.0, "predicted_exergy": 0.06}
            
        runtimes = [r.get('actual_minutes', 15.0) for r in wf_history]
        outcomes = [r.get('outcome_score', 1.0) for r in wf_history]
        exergies = [r.get('exergy_score', 0.06) for r in wf_history]
        
        # Simple Exponential Moving Average (EMA) - weight recent runs more
        def ema(values, alpha=0.3):
            res = values[0]
            for v in values[1:]:
                res = alpha * v + (1 - alpha) * res
            return res
            
        pred_runtime = ema(runtimes)
        pred_outcome = ema(outcomes)
        pred_exergy = ema(exergies)
        
        return {
            "predicted_runtime": round(pred_runtime, 2),
            "predicted_outcome": round(pred_outcome, 2),
            "predicted_exergy": round(pred_exergy, 4)
        }

    def lyapunov_scheduler(self, candidate_workflows: List[str]) -> List[Dict[str, Any]]:
        """Nivel 4: Ranks workflows by expected Exergy Density (Exergy / Runtime)."""
        ranked = []
        for wf in candidate_workflows:
            pred = self.predict(wf)
            exergy = pred["predicted_exergy"]
            runtime = pred["predicted_runtime"]
            
            # Priority = expected_exergy / runtime
            priority = exergy / runtime if runtime > 0 else 0
            
            ranked.append({
                "workflow": wf,
                "expected_exergy": exergy,
                "expected_runtime": runtime,
                "priority_score": round(priority, 4)
            })
            
        ranked.sort(key=lambda x: x["priority_score"], reverse=True)
        return ranked

    def genome_analysis(self) -> Dict[str, Dict[str, float]]:
        """Nivel 5: Analyze exergy across isolated genes instead of monolithic workflows."""
        gene_stats = {}
        
        for record in self.history:
            wf = record.get('workflow')
            exergy = record.get('exergy_score', 0)
            genes = self.genomes.get(wf, [])
            
            for gene in genes:
                if gene not in gene_stats:
                    gene_stats[gene] = []
                gene_stats[gene].append(exergy)
                
        results = {}
        for gene, scores in gene_stats.items():
            results[gene] = {
                "average_exergy": round(statistics.mean(scores), 4),
                "occurrences": len(scores)
            }
            
        # Sort by average exergy
        return dict(sorted(results.items(), key=lambda item: item[1]["average_exergy"], reverse=True))

    def evaluate_counterfactual(self, chosen_wf: str, discarded_wfs: List[str]) -> Dict[str, Any]:
        """Nivel 6: Calculate missed opportunity (Counterfactual Ledger)."""
        # Find the actual exergy achieved by the chosen workflow
        wf_history = [r for r in self.history if r.get('workflow') == chosen_wf]
        actual_exergy = wf_history[-1].get('exergy_score', 0) if wf_history else 0
        
        # Predict exergy for discarded workflows based on history prior to the chosen run
        # (For simplicity here, we just use current prediction engine)
        best_discarded_exergy = 0
        best_discarded_wf = None
        
        for wf in discarded_wfs:
            pred = self.predict(wf)
            if pred["predicted_exergy"] > best_discarded_exergy:
                best_discarded_exergy = pred["predicted_exergy"]
                best_discarded_wf = wf
                
        missed_opportunity = best_discarded_exergy - actual_exergy
        
        return {
            "chosen_workflow": chosen_wf,
            "actual_exergy": round(actual_exergy, 4),
            "best_alternative": best_discarded_wf,
            "alternative_expected_exergy": round(best_discarded_exergy, 4),
            "missed_opportunity": round(missed_opportunity, 4),
            "optimal_decision": actual_exergy >= best_discarded_exergy
        }

if __name__ == "__main__":
    engine = ExergyEngine()
    
    print("--- CORTEX ADAPTIVE RUNTIME: EXERGY ENGINE ---")
    print(f"Loaded {len(engine.history)} historical records.")
    
    print("\n[NIVEL 2] Entropy Drift Check (latest run):")
    workflows_run = list(set([r['workflow'] for r in engine.history]))
    for wf in workflows_run[:5]:
        drift = engine.get_entropy_drift(wf)
        if drift.get("status") == "DEGRADED":
            print(f" ⚠️  {wf} is DEGRADED! Expected: {drift['expected_exergy']}, Actual: {drift['actual_exergy']} ({drift['deviation_pct']}%)")
        elif drift.get("status") == "NOMINAL":
            print(f" ✅ {wf} is NOMINAL. (Expected: {drift['expected_exergy']}, Actual: {drift['actual_exergy']})")
            
    print("\n[NIVEL 4] Lyapunov Scheduler (Candidate Pool: ship, exergy-cascade, detective):")
    candidates = ["ship", "exergy-cascade", "detective"]
    ranked = engine.lyapunov_scheduler(candidates)
    for r in ranked:
        print(f" - {r['workflow']}: Priority {r['priority_score']} (Expected Exergy: {r['expected_exergy']}, Runtime: {r['expected_runtime']}m)")
        
    print("\n[NIVEL 5] Workflow Genome Analysis (Exergy per Gene):")
    genes = engine.genome_analysis()
    for g, stats in list(genes.items())[:5]:
        print(f" - Gene [{g}]: Avg Exergy {stats['average_exergy']} (Found in {stats['occurrences']} runs)")
        
    print("\n[NIVEL 6] Counterfactual Ledger Example:")
    # Mock example
    cf = engine.evaluate_counterfactual("ship", ["exergy-cascade", "detective"])
    print(f" Chosen: {cf['chosen_workflow']} -> {cf['actual_exergy']} exergy")
    print(f" Alternative: {cf['best_alternative']} -> {cf['alternative_expected_exergy']} expected exergy")
    if cf['optimal_decision']:
        print(" -> Decision was OPTIMAL.")
    else:
        print(f" -> SUBOPTIMAL. Missed opportunity: {cf['missed_opportunity']}")
