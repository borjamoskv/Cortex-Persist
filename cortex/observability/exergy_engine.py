import os
import json
import statistics
import random
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Tuple
from cortex.observability.efel import (
    SystemState, encode_state, encode_task, 
    build_failure_centroids, embedding_risk, efel_priority
)

CRONOS_LOG = os.path.expanduser("~/.gemini/config/skills/_metrics/cronos_memory.jsonl")
META_PARAMS_LOG = os.path.expanduser("~/.gemini/config/skills/_metrics/meta_params.json")
WORKFLOWS_DIR = os.path.expanduser("~/.agents/workflows")

@dataclass
class MetaParams:
    alpha_risk: float = 0.15
    learning_rate: float = 0.02
    epsilon: float = 0.05
    semantic_risk_weight: float = 0.2

@dataclass
class TaskStats:
    name: str
    exergy_mean: float
    exergy_var: float
    runtime_mean: float
    runtime_var: float
    confidence: float = 1.0

class ExergyEngine:
    """
    Core engine for CORTEX Adaptive Runtime.
    """
    def __init__(self):
        self.history = self._load_cronos_history()
        self.genomes = self._extract_workflow_genomes()
        self.meta = self._load_meta_params()
        self.failure_centroids = self._build_centroids()

    def _build_centroids(self):
        # Extract bad runs (e.g. outcome_score < 0.3 or success == False)
        bad_runs = [r for r in self.history if r.get('outcome_score', 1.0) < 0.4 or not r.get('success', True)]
        # We need a fake SystemState for historical runs to embed them. 
        # In a real system, the state would be logged in cronos_memory.jsonl.
        embeddings = []
        for r in bad_runs:
            s = SystemState(
                git_diff=r.get('git_diff', 'unknown'),
                ast_hash=r.get('ast_hash', 'unknown'),
                active_tasks=[r.get('workflow')],
                error_log=r.get('error_log', [])
            )
            embeddings.append(encode_state(s))
        return build_failure_centroids(embeddings)

    def _load_meta_params(self) -> MetaParams:
        if os.path.exists(META_PARAMS_LOG):
            try:
                with open(META_PARAMS_LOG, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return MetaParams(**data)
            except Exception:
                pass
        return MetaParams()

    def _save_meta_params(self):
        os.makedirs(os.path.dirname(META_PARAMS_LOG), exist_ok=True)
        with open(META_PARAMS_LOG, 'w', encoding='utf-8') as f:
            json.dump(asdict(self.meta), f, indent=2)

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

    def get_task_stats(self, workflow: str) -> TaskStats:
        """Calculates stable statistical moments for a workflow."""
        wf_history = [r for r in self.history if r.get('workflow') == workflow]
        if len(wf_history) < 2:
            return TaskStats(workflow, 0.06, 0.0, 15.0, 0.0, 0.1)
            
        runtimes = [r.get('actual_minutes', 15.0) for r in wf_history]
        exergies = [r.get('exergy_score', 0.06) for r in wf_history]
        
        exergy_mean = statistics.mean(exergies)
        exergy_var = statistics.variance(exergies) if len(exergies) > 1 else 0.0
        runtime_mean = statistics.mean(runtimes)
        runtime_var = statistics.variance(runtimes) if len(runtimes) > 1 else 0.0
        
        # Confidence decays if variance is high relative to mean
        cv = (exergy_var**0.5) / (exergy_mean + 1e-6)
        confidence = max(0.1, 1.0 - min(cv, 0.9))
        
        return TaskStats(workflow, exergy_mean, exergy_var, runtime_mean, runtime_var, confidence)

    def lyapunov_scheduler(self, candidate_workflows: List[str], state: SystemState = None) -> List[Dict[str, Any]]:
        """Nivel 4: EFEL Meta-Lyapunov Scheduler. Risk-penalized Exergy Density in Embedding Space."""
        ranked = []
        for wf in candidate_workflows:
            stats = self.get_task_stats(wf)
            
            if state and self.failure_centroids is not None and len(self.failure_centroids) > 0:
                # EFEL context-aware priority
                priority = efel_priority(stats, state, self.meta, self.failure_centroids)
            else:
                # Fallback flat statistical priority
                risk_penalty = self.meta.alpha_risk * stats.exergy_var
                base_score = (stats.exergy_mean - risk_penalty) / (stats.runtime_mean + 1e-6)
                priority = base_score * stats.confidence
            
            ranked.append({
                "workflow": wf,
                "expected_exergy": stats.exergy_mean,
                "exergy_variance": stats.exergy_var,
                "expected_runtime": stats.runtime_mean,
                "priority_score": round(max(0.0, priority), 4)
            })
            
        ranked.sort(key=lambda x: x["priority_score"], reverse=True)
        
        # Epsilon-greedy forced exploration to prevent self-fulfilling bias
        if candidate_workflows and random.random() < self.meta.epsilon:
            exploring = random.choice(ranked)
            exploring["priority_score"] = float('inf') # Force to top
            exploring["is_exploration"] = True
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
            stats = self.get_task_stats(wf)
            if stats.exergy_mean > best_discarded_exergy:
                best_discarded_exergy = stats.exergy_mean
                best_discarded_wf = wf
                
        missed_opportunity = best_discarded_exergy - actual_exergy
        
        return {
            "type": "counterfactual_miss" if missed_opportunity > 0 else "optimal",
            "chosen_workflow": chosen_wf,
            "actual_exergy": round(actual_exergy, 4),
            "best_alternative": best_discarded_wf,
            "alternative_expected_exergy": round(best_discarded_exergy, 4),
            "miss_cost": round(missed_opportunity, 4),
            "task_variance": self.get_task_stats(chosen_wf).exergy_var,
            "optimal_decision": actual_exergy >= best_discarded_exergy
        }

    def evolve(self, window_size: int = 1000) -> Dict[str, Any]:
        """Update Meta-Lyapunov alpha_risk based on counterfactual historical errors."""
        ledger_events = []
        
        # Generate counterfactuals from history simulating an evaluation context
        # (For simplicity, evaluate each past run against the other active candidates)
        active_wfs = list(set([r.get('workflow') for r in self.history]))
        recent_history = self.history[-window_size:] if len(self.history) > window_size else self.history
        
        for record in recent_history:
            wf = record.get('workflow')
            discarded = [w for w in active_wfs if w != wf]
            cf = self.evaluate_counterfactual(wf, discarded)
            ledger_events.append(cf)
            
        total_error = 0.0
        grad = 0.0
        miss_count = 0
        
        for event in ledger_events:
            if event["type"] != "counterfactual_miss":
                continue
                
            error = event["miss_cost"]
            variance = event["task_variance"]
            
            total_error += error
            # If high variance caused a miss, alpha risk needs to increase
            grad += error * variance
            miss_count += 1
            
        old_alpha = self.meta.alpha_risk
        
        # Gradient update
        self.meta.alpha_risk += self.meta.learning_rate * grad
        self.meta.alpha_risk *= 0.999 # Entropy bleed
        self.meta.alpha_risk = max(0.0, min(self.meta.alpha_risk, 1.0))
        
        self._save_meta_params()
        
        return {
            "old_alpha": old_alpha,
            "new_alpha": self.meta.alpha_risk,
            "counterfactual_loss": total_error,
            "miss_count": miss_count
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
            
    print("\n[NIVEL 4] Lyapunov Scheduler (Candidate Pool: cron_health_check, memory_reconciliation, ingest_pipeline, vector_compaction, adversarial_simulation):")
    candidates = ["cron_health_check", "memory_reconciliation", "ingest_pipeline", "vector_compaction", "adversarial_simulation"]
    ranked = engine.lyapunov_scheduler(candidates)
    for r in ranked:
        print(f" - {r['workflow']}: Priority {r['priority_score']} (Expected Exergy: {r['expected_exergy']}, Runtime: {r['expected_runtime']}m)")
        
    print("\n[NIVEL 5] Workflow Genome Analysis (Exergy per Gene):")
    genes = engine.genome_analysis()
    for g, stats in list(genes.items())[:5]:
        print(f" - Gene [{g}]: Avg Exergy {stats['average_exergy']} (Found in {stats['occurrences']} runs)")
        
    print("\n[NIVEL 6] Counterfactual Ledger Example:")
    # Assume the agent chose "adversarial_simulation" because a human demanded it, ignoring the scheduler.
    cf = engine.evaluate_counterfactual("adversarial_simulation", ["cron_health_check", "memory_reconciliation"])
    print(f" Decisión tomada: {cf['chosen_workflow']} -> {cf['actual_exergy']} exergía real extraída")
    print(f" Mejor alternativa según Lyapunov: {cf['best_alternative']} -> {cf['alternative_expected_exergy']} exergía esperada")
    if cf['optimal_decision']:
        print(" -> Decision was OPTIMAL.")
    else:
        print(f" -> ERROR TÁCTICO. Missed opportunity (Coste de oportunidad): {cf['missed_opportunity']}")
