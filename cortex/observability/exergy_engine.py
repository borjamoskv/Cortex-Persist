import os
import json
import statistics
import random
from dataclasses import dataclass, asdict
from typing import Any
from cortex.observability.efel import SystemState, encode_state, encode_task
from cortex.observability.fdf import FailureField, Particle, simulate_field
from cortex.observability.caf import select_next, lagrangian
import numpy as np
import time

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


@dataclass
class ExecutionTrace:
    task: str
    predicted_action: float
    real_cost: float
    real_exergy: float
    fdf_shift: float


def inject_reality_noise(state_vec: np.ndarray) -> np.ndarray:
    """Grounding injection: Evita feedback loop de realidad simulada."""
    git_entropy = np.random.uniform(-1, 1, size=state_vec.shape)
    try:
        load = os.getloadavg()[0]
    except AttributeError:
        load = 1.0
    runtime_noise = np.full_like(state_vec, load)
    return state_vec + 0.05 * git_entropy + 0.02 * runtime_noise


class ExergyEngine:
    """
    Core engine for CORTEX Adaptive Runtime.
    """

    def __init__(self):
        from cortex.observability.ouroboros import OuroborosEngine

        self.history = self._load_cronos_history()
        self.genomes = self._extract_workflow_genomes()
        self.meta = self._load_meta_params()
        self.failure_field = self._build_failure_field()
        self.ouroboros = OuroborosEngine()

    def _build_failure_field(self):
        bad_runs = [
            r
            for r in self.history
            if r.get("outcome_score", 1.0) < 0.4 or not r.get("success", True)
        ]
        embeddings = []
        for r in bad_runs:
            wf_name = r.get("workflow")
            stats = self.get_task_stats(wf_name)
            s = SystemState(
                git_diff=r.get("git_diff", "unknown"),
                ast_hash=r.get("ast_hash", "unknown"),
                active_tasks=[wf_name],
                error_log=r.get("error_log", []),
            )
            state_vec = encode_state(s)
            task_vec = encode_task(stats)
            x = np.concatenate([task_vec, state_vec])
            embeddings.append(x)

        field = FailureField()
        if embeddings:
            field.fit(np.array(embeddings))
        return field

    def _load_meta_params(self) -> MetaParams:
        if os.path.exists(META_PARAMS_LOG):
            try:
                with open(META_PARAMS_LOG, encoding="utf-8") as f:
                    data = json.load(f)
                    return MetaParams(**data)
            except Exception:
                pass
        return MetaParams()

    def _save_meta_params(self):
        os.makedirs(os.path.dirname(META_PARAMS_LOG), exist_ok=True)
        with open(META_PARAMS_LOG, "w", encoding="utf-8") as f:
            json.dump(asdict(self.meta), f, indent=2)

    def _load_cronos_history(self) -> list[dict[str, Any]]:
        records = []
        if os.path.exists(CRONOS_LOG):
            with open(CRONOS_LOG, encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        records.append(json.loads(line))
        return records

    def _extract_workflow_genomes(self) -> dict[str, list[str]]:
        """Extracts 'genes' (tools, keywords, paradigms) from workflows."""
        genomes = {}
        if not os.path.exists(WORKFLOWS_DIR):
            return genomes

        for file in os.listdir(WORKFLOWS_DIR):
            if not file.endswith(".md"):
                continue
            wf_name = file.replace(".md", "")
            genes = set()
            with open(os.path.join(WORKFLOWS_DIR, file), encoding="utf-8") as f:
                content = f.read().lower()

                # Gene extraction heuristics
                if "python" in content or "script" in content:
                    genes.add("python")
                if "sql" in content or "database" in content or "sqlite" in content:
                    genes.add("sql")
                if "mcp" in content:
                    genes.add("mcp")
                if "search" in content or "brave" in content:
                    genes.add("search")
                if "browser" in content or "scraping" in content:
                    genes.add("browser")
                if "github" in content or "pr" in content:
                    genes.add("github")
                if "visual" in content or "ui" in content or "css" in content:
                    genes.add("frontend")
                if "plan" in content or "architecture" in content:
                    genes.add("planning")

            genomes[wf_name] = list(genes)
        return genomes

    def get_entropy_drift(self, workflow: str) -> dict[str, Any]:
        """Nivel 2: Detects entropy drift based on recent exergy vs historical."""
        wf_history = [r for r in self.history if r.get("workflow") == workflow]
        if len(wf_history) < 3:
            return {"status": "INSUFFICIENT_DATA"}

        scores = [r.get("exergy_score", 0) for r in wf_history]
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
            "status": status,
        }

    def get_task_stats(self, workflow: str) -> TaskStats:
        """Calculates stable statistical moments for a workflow."""
        wf_history = [r for r in self.history if r.get("workflow") == workflow]
        if len(wf_history) < 2:
            return TaskStats(workflow, 0.06, 0.0, 15.0, 0.0, 0.1)

        runtimes = [r.get("actual_minutes", 15.0) for r in wf_history]
        exergies = [r.get("exergy_score", 0.06) for r in wf_history]

        exergy_mean = statistics.mean(exergies)
        exergy_var = statistics.variance(exergies) if len(exergies) > 1 else 0.0
        runtime_mean = statistics.mean(runtimes)
        runtime_var = statistics.variance(runtimes) if len(runtimes) > 1 else 0.0

        # Confidence decays if variance is high relative to mean
        cv = (exergy_var**0.5) / (exergy_mean + 1e-6)
        confidence = max(0.1, 1.0 - min(cv, 0.9))

        return TaskStats(workflow, exergy_mean, exergy_var, runtime_mean, runtime_var, confidence)

    def lyapunov_scheduler(
        self, candidate_workflows: list[str], state: SystemState = None
    ) -> list[dict[str, Any]]:
        """Nivel 8: Multi-Agent Field Physics. Descenso de energía global de partículas."""
        if not candidate_workflows:
            return []

        # 1. Create Particles
        particles = []
        state_vec = encode_state(state) if state else np.zeros(32)  # Dummy state

        for wf in candidate_workflows:
            stats = self.get_task_stats(wf)
            task_vec = encode_task(stats)

            # Position is concatenated task and state
            position = np.concatenate([task_vec, state_vec])
            velocity = np.zeros_like(position)
            mass = 1.0 / (stats.exergy_mean + 1e-6)

            particles.append(
                Particle(
                    task_name=wf,
                    position=position,
                    velocity=velocity,
                    mass=mass,
                    original_stats=stats,
                )
            )

        # 2. Lagrangian Action Minimization (Variational Monte Carlo)
        if self.failure_field.fitted:
            # First, simulate field just briefly to acquire history/memory gravity
            # then use CAF for global action minimization. Or we skip simulate_field
            # and let CAF just use the static histories if we persist them.
            # For now, simulate briefly to build the CTC 'history' curvature.
            simulate_field(particles, self.failure_field, steps=10, dt=0.1)

        ordered_particles = select_next(particles, state_vec, self.failure_field, self.meta)

        # 3. Collapse to final Lagrangian action states
        scored = []
        for p in ordered_particles:
            L = lagrangian(p, state_vec, self.meta, self.failure_field)
            dt = (
                p.original_stats.runtime_mean
                if getattr(p.original_stats, "runtime_mean", 0) > 0
                else 1.0
            )
            S = -L * dt

            scored.append(
                {
                    "workflow": p.task_name,
                    "expected_exergy": p.original_stats.exergy_mean,
                    "exergy_variance": p.original_stats.exergy_var,
                    "expected_runtime": p.original_stats.runtime_mean,
                    "action_cost": round(S, 4),
                    "priority_score": round(
                        -S, 4
                    ),  # For CLI sorting compatibility (higher is better)
                }
            )

        # select_next already sorted them by action cost, so scored is in correct order
        return scored

    def autonomous_field_daemon(
        self,
        horizon: int = 5,
        epsilon_path: float = 0.1,
        recompute_fdf_min: int = 10,
        max_cycles: int = 5,
    ):
        """
        AEFM: Autonomous Exergy Field Mode.
        Ciclo infinito de: observe -> deform field -> simulate futures -> collapse action -> execute -> update geometry
        """
        import logging

        log = logging.getLogger("CORTEX-AEFM")
        log.info("🌌 Iniciando Autonomous Exergy Field Mode (AEFM)")

        last_fdf = time.time()
        candidates = list(self.genomes.keys())

        for cycle in range(max_cycles):
            log.info(f"⚡ [Cycle {cycle}] Observer & Reality Grounding...")

            if time.time() - last_fdf > recompute_fdf_min * 60:
                log.info("🔄 Recomputing Failure Density Field (Geometry Update)...")
                self.failure_field = self._build_failure_field()
                last_fdf = time.time()

            # 1. Observe & Noise (Grounding)
            dummy_state = SystemState(
                git_diff="daemon", ast_hash="daemon", active_tasks=[], error_log=[]
            )
            base_state_vec = encode_state(dummy_state)
            inject_reality_noise(base_state_vec)

            # 2. Simulate Futures & Collapse Action
            scored = self.lyapunov_scheduler(
                candidates, dummy_state
            )  # lyapunov_scheduler now uses CAF under the hood
            if not scored:
                break

            winner = scored[0]
            predicted_action = winner["action_cost"]

            log.info(
                f"🔮 Collapsed future trajectory. Winner: {winner['workflow']} (Predicted Action: {predicted_action})"
            )

            # 3. "Execute" & Measure Reality (Mock execution for now)
            start_time = time.time()
            time.sleep(1)  # Fake run
            real_runtime = (time.time() - start_time) / 60.0

            # 4. Telemetry: Update Geometry
            # En un entorno real, exergy se extraería del output. Asumimos fluctuación.
            real_exergy = winner["expected_exergy"] * np.random.uniform(0.8, 1.2)

            trace = ExecutionTrace(
                task=winner["workflow"],
                predicted_action=predicted_action,
                real_cost=real_runtime,
                real_exergy=real_exergy,
                fdf_shift=np.abs(predicted_action - real_exergy),
            )

            # Ouroboros Engine Injection
            self.ouroboros.inject_telemetry(trace)

            log.info(f"🪐 Telemetry Tracked: {trace}")

            safe_signals = self.ouroboros.get_safe_optimization_signal()
            if safe_signals:
                log.info(f"🧬 Delayed Economic Signals Active: {safe_signals}")

            log.info("---")
            time.sleep(2)

        log.info("🌌 AEFM Cycle Limit Reached (Safe Stop).")

    def genome_analysis(self) -> dict[str, dict[str, float]]:
        """Nivel 5: Analyze exergy across isolated genes instead of monolithic workflows."""
        gene_stats = {}

        for record in self.history:
            wf = record.get("workflow")
            exergy = record.get("exergy_score", 0)
            genes = self.genomes.get(wf, [])

            for gene in genes:
                if gene not in gene_stats:
                    gene_stats[gene] = []
                gene_stats[gene].append(exergy)

        results = {}
        for gene, scores in gene_stats.items():
            results[gene] = {
                "average_exergy": round(statistics.mean(scores), 4),
                "occurrences": len(scores),
            }

        # Sort by average exergy
        return dict(
            sorted(results.items(), key=lambda item: item[1]["average_exergy"], reverse=True)
        )

    def evaluate_counterfactual(self, chosen_wf: str, discarded_wfs: list[str]) -> dict[str, Any]:
        """Nivel 6: Calculate missed opportunity (Counterfactual Ledger)."""
        # Find the actual exergy achieved by the chosen workflow
        wf_history = [r for r in self.history if r.get("workflow") == chosen_wf]
        actual_exergy = wf_history[-1].get("exergy_score", 0) if wf_history else 0

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
            "optimal_decision": actual_exergy >= best_discarded_exergy,
        }

    def evolve(self, window_size: int = 1000) -> dict[str, Any]:
        """Update Meta-Lyapunov alpha_risk based on counterfactual historical errors."""
        ledger_events = []

        # Generate counterfactuals from history simulating an evaluation context
        # (For simplicity, evaluate each past run against the other active candidates)
        active_wfs = list(set([r.get("workflow") for r in self.history]))
        recent_history = (
            self.history[-window_size:] if len(self.history) > window_size else self.history
        )

        for record in recent_history:
            wf = record.get("workflow")
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
        self.meta.alpha_risk *= 0.999  # Entropy bleed
        self.meta.alpha_risk = max(0.0, min(self.meta.alpha_risk, 1.0))

        self._save_meta_params()

        return {
            "old_alpha": old_alpha,
            "new_alpha": self.meta.alpha_risk,
            "counterfactual_loss": total_error,
            "miss_count": miss_count,
        }
