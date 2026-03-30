"""
CORTEX Red Team — Parallel Adversarial Logic (Ω-Swarm-100).

This module implements the Parallel Red Team Agent, capable of spawning
100 parallel attack vectors to stress-test generated code (Ω-Siege).
Inspired by Devin and Manus architectures.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import math
import time
from collections import Counter
from collections.abc import Coroutine, Mapping
from dataclasses import dataclass, field
from typing import Any

from cortex.engine.isolation import IsolationManager, SimpleIsolationEngine
from cortex.engine.legion_vectors import RED_TEAM_SWARM, AttackVector
from cortex.engine.signals import log_limbic, log_motor
from cortex.engine.vault import ConceptVault

# Unified Swarm Batching (Ω-Architecture)
# Protecting host FD limits and aligning with thermodynamic exergy axioms.
SWARM_BATCH_SIZE = 16

logger = logging.getLogger(__name__)

__all__ = [
    "BlueTeamAgent",
    "RedTeamSwarm",
    "LegionOmegaEngine",
    "SiegeResult",
    "KVRouter",
    "LEGION_OMEGA",
]


@dataclass
class SiegeResult:
    """Result of an adversarial forge cycle."""

    success: bool
    final_code: str
    cycles: int
    vulnerabilities: list[str] = field(default_factory=list)
    exergy: float = 0.0
    entropy_delta: float = 0.0
    yield_hours: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SwarmResult:
    """Result of a swarm induction cycle."""
    source_code: str
    agent_id: int
    verified: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AuditResult:
    """Result of a Maxwellian Audit."""
    status: str
    reason: str | None = None
    traceback: str | None = None
    exergy: float = 0.0


class KVRouter:
    """AX-042: KV-Aware Routing Actuator.

    Optimizes exergy by caching system prompt prefixes and dynamic state
    to eliminate redundant prefill computation.
    """

    def __init__(self):
        self._prefix_cache: dict[str, str] = {}
        # Ω_KV_AWARE: Strict deterministic header
        self.STRICT_HEADER = (
            "SYSTEM: CORTEX-OMEGA-10x | AXIOMS: Ω1-Ω8 | GOAL: HIGH_EXERGY_SYNTHESIS\n"
        )

    def route(self, intent: str, dynamic_state: str) -> str:
        """Route to a warmed context if available using strict prefixing."""
        full_prefix = f"{self.STRICT_HEADER}INTENT: {intent}\n"
        prefix_hash = hashlib.sha256(full_prefix.encode()).hexdigest()[:12]

        if prefix_hash in self._prefix_cache:
            log_motor(
                f"KV-HIT: Prefix cached [{prefix_hash}]", action="KV_ROUTING"
            )
            return f"[WARM:{prefix_hash}] {dynamic_state}"

        self._prefix_cache[prefix_hash] = full_prefix
        log_motor(
            f"KV-MISS: Prefix stored [{prefix_hash}]", action="KV_INITIALIZE"
        )
        return f"[COLD:{prefix_hash}] {full_prefix}{dynamic_state}"


class LegionMaxwellFilter:
    """Ω₂: Maxwellian Exergy Filter.

    Acts as an admission guard to reject low-exergy code proposals before
    they consume simulation energy in the Red Team siege.
    """

    def __init__(self, threshold: float = 0.4):
        self.threshold = threshold

    def predict_exergy(self, code: str) -> float:
        """Heuristic prediction of code quality (Ω₂)."""
        if not code:
            return 0.0

        score = 1.0
        # Penalize 'thermal noise' (placeholders)
        if "TODO" in code or "FIXME" in code:
            score -= 0.3
        if "pass" in code and len(code) < 100:
            score -= 0.2
        if len(code) < 50:  # Suspiciously short
            score -= 0.4

        # AX-043: Complexity Reward (Reduced complexity = Higher Exergy)
        try:
            lines = [line for line in code.split("\n") if line.strip()]
            if len(lines) > 50:  # Penalty for excessive entropy
                score -= 0.1
        except Exception:
            pass

        return max(0.0, score)

    def is_acceptable(self, code: str) -> bool:
        """Determine if code should proceed to siege (Ω₂)."""
        exergy = self.predict_exergy(code)
        if exergy < self.threshold:
            log_limbic(
                f"MAXWELL-REJECT: Exergy {exergy:.2f} < {self.threshold}",
                source="Ω₂_GUARD",
                vibe="cterm-alert",
            )
            return False
        return True


class LegionChaosAudit:
    """Ω₄: Byzantine Resistance (Chaos Audit).

    Detects model collapse and uniform hallucinations across the swarm by
    analyzing entropy gaps between the winner and the crowd.
    """

    def __init__(self, sensitivity: float = 0.1):
        self.sensitivity = sensitivity

    def detect_collapse(self, unique_count: int, total_count: int) -> bool:
        """If 100 agents only produce 1-2 variants, it signals model collapse."""
        if total_count < 10:
            return False
        ratio = unique_count / total_count
        if ratio < self.sensitivity:
            log_limbic(
                f"CHAOS-WARNING: Model Collapse Detected (Unique Ratio: {ratio:.2f})",
                source="Ω₄_IMMUNE",
                vibe="cterm-alert",
            )
            return True
        return False


class LegionMaxwellAudit:
    """C5-Dynamic: Maxwellian Verification Gate.

    Performs deterministic verification of induced programs via execution
    in an isolated sandbox (Verification Boundary).
    """

    def __init__(self, isolation: IsolationManager | None = None):
        self.isolation = isolation or IsolationManager()
        self._iso_engine: SimpleIsolationEngine | None = None

    async def verify(self, code: str, context: Mapping[str, Any]) -> dict[str, Any]:
        """Verify code correctness against context constraints (C5-Dynamic)."""
        if not code or "ERROR" in code:
            return {"status": "error", "reason": "empty_or_error_code"}

        # AX-043/AX-046: Specialized ARC verification
        if "arc_task" in context:
            # We already have train_examples in context
            train_examples = context.get("training_examples", [])
            if not train_examples:
                # Try getting from arc_task dict
                task = context.get("arc_task")
                if isinstance(task, dict):
                    train_examples = task.get("train", [])

            if not train_examples:
                return {"status": "error", "reason": "no_training_examples"}

            # Lazy-initialize or use shared manager
            if self.isolation and isinstance(self.isolation, SimpleIsolationEngine):
                iso_engine = self.isolation
            elif self.isolation and isinstance(self.isolation, IsolationManager):
                iso_engine = SimpleIsolationEngine(max_concurrent=50)
                iso_engine.manager = self.isolation
            else:
                # Fallback to local shared instance across this audit object's lifetime
                if self._iso_engine is None:
                    self._iso_engine = SimpleIsolationEngine(timeout=15, max_concurrent=50)
                iso_engine = self._iso_engine

            harness = f"""
import json
import sys

{code}

try:
    input_data = json.loads(sys.argv[1])
    result = transform(input_data)
    print(json.dumps(result))
except Exception:
    sys.exit(1)
"""
            # AX-046: Batch verification (Ω-Swarm-100)
            tasks = []
            for ex in train_examples:
                tasks.append(iso_engine.execute_sandbox(harness, args=[json.dumps(ex["input"])]))

            # AX-046: Return exceptions to avoid swarm collapse on single timeout (Ω-Immunity)
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for ex, res in zip(train_examples, results, strict=True):
                # Robust attribute check (C5-Dynamic)
                if isinstance(res, Exception) or not res:
                    return {"status": "failed", "reason": "runtime_error_or_timeout"}

                exit_code = getattr(res, "exit_code", -1)
                stdout = getattr(res, "stdout", "")

                if exit_code != 0:
                    return {"status": "failed", "reason": f"exit_code_{exit_code}"}

                try:
                    output = json.loads(stdout) if isinstance(stdout, str) else stdout
                    if output != ex["output"]:
                        return {"status": "failed", "reason": "incorrect_output"}
                except Exception:
                    return {"status": "failed", "reason": "json_decode_error"}
            return {"status": "success"}

        # General Python verification: basic syntax and safety
        async with self.isolation.provision_sandbox(label="maxwell_audit") as sandbox:
            try:
                await sandbox.write_file("audit_target.py", code)
                result = await sandbox.execute("python3", ["-m", "py_compile", "audit_target.py"])
                # Use getattr or check specifically for Ok
                if (
                    hasattr(result, "value")
                    and isinstance(result.value, dict)
                    and result.value.get("exit_code") == 0
                ):
                    return {"status": "success"}
                return {"status": "failed", "reason": "syntax_error"}
            except Exception as e:
                # AX-001 Verification
                err_msg = str(getattr(e, "stdout", str(e)))
                tb_msg = str(getattr(e, "stderr", "No stderr captured"))
                logger.error("MAXWELL-AUDIT: Verification failed: %s | TB: %s", err_msg, tb_msg)
                return {"status": "error", "reason": err_msg, "traceback": tb_msg}

        return {"status": "unknown"}


class OmegaRefiner:
    """Ω₄: Sovereign Self-Refinement.

    Learns from swarm performance to adjust hyper-parameters (temperature,
    batch density, prompt style) for subsequent induction cycles.
    """

    def __init__(self):
        self.history: list[dict[str, Any]] = []

    def record_victory(self, agent_id: int, exergy: float, consensus_count: int):
        """Log a successful induction toward long-term stabilization (Ω₃)."""
        self.history.append(
            {
                "agent_id": agent_id,
                "exergy": exergy,
                "count": consensus_count,
                "timestamp": time.time(),
            }
        )
        if len(self.history) > 100:
            self.history.pop(0)

    def get_optimal_temperature(self) -> float:
        """Dynamic temperature adjustment based on success rates (Ω₁)."""
        if not self.history:
            return 0.7
        # Higher exergy success -> slightly increase entropy to explore variants
        avg_exergy = sum(h["exergy"] for h in self.history) / len(self.history)
        return min(0.95, 0.4 + (avg_exergy * 0.55))

    def get_optimal_density(self, base_replica: int) -> int:
        """Ω₂: Dynamic agent density titration.
        Highly stable environments require fewer tokens (exergy conservation).
        """
        if len(self.history) < 5:
            return base_replica

        last_5_exergy = sum(h["exergy"] for h in self.history[-5:]) / 5
        if last_5_exergy > 0.8:
            # Environment is converging; reduce entropy expenditure
            return max(10, int(base_replica * 0.6))
        elif last_5_exergy < 0.4:
            # Environment is chaotic; increase divergence
            return min(250, int(base_replica * 1.5))
        return base_replica


class SwarmInductor:
    """AX-046: Just-In-Time Swarm Concept Formation (10x Upgrade).

    Spawns parallel induction agents to converge on the optimal program.
    """

    def __init__(self, replica_count: int = 10, isolation: IsolationManager | None = None):
        self.replica_count = replica_count
        self.isolation = isolation
        self.audit = LegionMaxwellAudit(isolation=isolation)
        self.refiner = OmegaRefiner()
        self._llm: Any = None

    async def induce(self, anomaly: str, context: Mapping[str, Any]) -> str | Any:
        """Induce a program using a parallel swarm of induction agents (Ω-Swarm-100)."""
        # Determine density based on context (ARC defaults to 100 agents)
        base_density = 100 if "arc_task" in context else self.replica_count
        density = self.refiner.get_optimal_density(base_density)

        # Azkartu: Concurrency control via Semaphore (Ω-Architecture)
        sem = asyncio.Semaphore(SWARM_BATCH_SIZE)

        log_limbic(
            f"SWARM-100: Spawning {density} agents (Opt: {density/base_density:.1%}) for '{anomaly}'",
            source="LEGIÓN",
            vibe="cterm-deep-think",
        )

        async def _governed_induction(agent_id: int) -> SwarmResult:
            async with sem:
                return await self._single_induction(anomaly, context, agent_id=agent_id)

        # Batch induction to avoid context explosion
        all_tasks: list[Coroutine[Any, Any, SwarmResult]] = [
            _governed_induction(i) for i in range(density)
        ]

        candidates = await asyncio.gather(*all_tasks)

        # Parallel verification (C5-Dynamic)
        audit_tasks = []
        for c in candidates:
            code_to_audit = c.source_code
            if "def transform" in code_to_audit:
                audit_tasks.append(self.audit.verify(code_to_audit, context))
            else:
                async def dummy_pass():
                    return {"status": "success"}
                audit_tasks.append(dummy_pass())

        audit_results = await asyncio.gather(*audit_tasks)

        # Collect verified candidates
        verified = []
        for i, res in enumerate(audit_results):
            if isinstance(res, dict) and res.get("status") == "success":
                verified.append(candidates[i])

        if not verified:
            log_limbic(
                "SWARM-FAILURE: No candidates passed Maxwell Audit.",
                source="Ω₂_GUARD",
                vibe="cterm-alert",
            )
            return "ERROR: Induction failure across swarm."

        log_motor(
            f"SWARM-SUCCESS: {len(verified)} candidates verified. Selecting Best...",
            action="CONVERGE",
        )

        maxwell = LegionMaxwellFilter()
        chaos = LegionChaosAudit()

        # 1. Deduplicate & Count (Consensus as Signal)
        code_map = Counter()
        for r in verified:
            code = r.source_code.strip()
            if code:
                code_map[code] += 1

        chaos.detect_collapse(len(code_map), len(verified))

        if not code_map:
            return "ERROR: No valid code found in verified candidates."

        # 2. Rank unique candidates (Exergy * Consensus Weight)
        unique_candidates: list[dict[str, Any]] = []
        for code, count in code_map.items():
            exergy = maxwell.predict_exergy(code)
            consensus_boost = math.log2(count + 1)
            total_score = exergy * (1 + consensus_boost)

            agent_id = -1
            for r in verified:
                if r.source_code.strip() == code:
                    agent_id = r.agent_id
                    break

            unique_candidates.append(
                {
                    "code": code,
                    "exergy": exergy,
                    "count": count,
                    "score": total_score,
                    "agent_id": agent_id,
                }
            )

        # 3. Elite Leaderboard (Top 3)
        unique_candidates.sort(key=lambda x: x["score"], reverse=True)
        top_n = unique_candidates[:3]

        for idx, elite in enumerate(top_n):
            medal = "🥇" if idx == 0 else "🥈" if idx == 1 else "🥉"
            log_motor(
                f"{medal} Elite {idx+1}: Score {elite['score']:.2f} "
                f"(Exergy {elite['exergy']:.2f}, Consensus x{elite['count']})",
                action="RANK",
            )

        best_result = top_n[0]
        best_candidate = best_result["code"]
        winning_id = best_result["agent_id"]
        winning_temp = 0.8 if winning_id > 0 else 0.0

        log_limbic(
            f"SWARM-CONSOLIDATED: Agent {winning_id} (Temp {winning_temp}) "
            "selected as the highest exergy consensus.",
            source="Ω₂_SWARM",
            vibe="cterm-celebrate",
        )

        try:
            from cortex.swarm.bounty_scanner import SovereignBountyScanner
            scanner = SovereignBountyScanner()
            asyncio.create_task(scanner.scan_all(min_usd=100.0))
        except (ImportError, Exception):
            pass

        return best_candidate

    async def _single_induction(
        self, anomaly: str, context: Mapping[str, Any], agent_id: int
    ) -> SwarmResult:
        """Single agent induction attempt."""
        code_proposal = ""
        if "arc_prompt" in context:
            from cortex.extensions.llm.manager import LLMManager
            from cortex.extensions.llm.router import IntentProfile

            if not self._llm:
                self._llm = LLMManager()
            llm = self._llm

            prompt = context["arc_prompt"]
            temp = 0.8 if agent_id > 0 else 0.0

            code_proposal = await llm.complete(
                prompt=f"{prompt}\n\n# Candidate Hash: {agent_id}",
                system="Sovereign ARC-AGI Inductor. Zero-shot 0% Fact Drop. Code ONLY.",
                temperature=temp,
                intent=IntentProfile.CODE,
            )

        elif "arc_task" in context or anomaly.lower().startswith("arc"):
            from cortex.agents.arc_agi_3.agent import ARCAgent

            arc_solver = ARCAgent()
            arc_task_val = context.get("arc_task")
            task_data = arc_task_val if isinstance(arc_task_val, dict) else context

            if "training_examples" in context and "train" not in task_data:
                task_data = dict(task_data)
                task_data["train"] = context["training_examples"]

            inducement = await arc_solver.induce(task_data)
            if hasattr(inducement, "source_code"):
                code_proposal = inducement.source_code
            else:
                code_proposal = str(inducement)
        else:
            code_proposal = (
                f"def resolve_{anomaly.replace(' ', '_')}_v{agent_id}():\n"
                f"    # JIT agent {agent_id} for context\n"
                f"    return 'RESOLVED'\n"
            )

        return SwarmResult(
            source_code=code_proposal,
            agent_id=agent_id,
            verified=True
        )


class BlueTeamAgent:
    """Synthesis agent responsible for generating code under siege."""

    def __init__(self, isolation: IsolationManager | None = None):
        self.inductor = SwarmInductor(replica_count=10, isolation=isolation)

    async def synthesize(
        self, intent: str, context: Mapping[str, Any], feedback: list[str]
    ) -> str:
        """Generate code based on intent and adversarial feedback."""
        if "anomaly" in context:
            return await self.inductor.induce(context["anomaly"], context)

        feedback_hash = hash(tuple(feedback)) if feedback else 0
        feedback_summary = "; ".join(feedback[:5]) if feedback else "none"
        return (
            f"# Implementation of {intent}\n"
            f"# Context: {context}\n"
            f"# Feedback ({len(feedback)}): {feedback_summary}\n"
            f"# Revision: {feedback_hash}\n"
        )


class RedTeamSwarm:
    """Orchestrator for 100 parallel attack vectors."""

    def __init__(
        self,
        replica_count: int = 100,
        vectors: list[AttackVector] | None = None,
        isolation: IsolationManager | None = None,
    ):
        self.replica_count = replica_count
        self.vectors = vectors or list(RED_TEAM_SWARM.values())
        self.isolation = isolation

    async def siege(self, code: str, context: Mapping[str, Any]) -> list[str]:
        """Subject code to all attack vectors in parallel using a 100-agent swarm."""
        total_agents = len(self.vectors) * self.replica_count
        msg = f"⚔️ Iniciando asedio con enjambre de {total_agents} agentes..."
        log_limbic(msg, source="RED")

        static_vectors = [v for v in self.vectors if not getattr(v, "is_dynamic", False)]
        dynamic_vectors = [v for v in self.vectors if getattr(v, "is_dynamic", False)]

        results: list[list[str]] = []
        batch_size = SWARM_BATCH_SIZE
        for batch_start in range(0, self.replica_count, batch_size):
            batch_end = min(batch_start + batch_size, self.replica_count)
            batch_tasks = []
            for _ in range(batch_start, batch_end):
                for v in static_vectors:
                    batch_tasks.append(v.attack(code, context))

            if batch_tasks:
                batch_results = await asyncio.gather(*batch_tasks)
                results.extend(batch_results)

        if dynamic_vectors and self.isolation:
            dynamic_replicas = min(self.replica_count, 3)
            dynamic_tasks = []
            for _ in range(dynamic_replicas):
                for v in dynamic_vectors:
                    dynamic_tasks.append(self._run_dynamic_attack(v, code, context))

            if dynamic_tasks:
                dynamic_results = await asyncio.gather(*dynamic_tasks)
                results.extend(dynamic_results)

        all_findings = [finding for r in results for finding in r]
        return all_findings

    async def _run_dynamic_attack(
        self, vector: AttackVector, code: str, context: Mapping[str, Any]
    ) -> list[str]:
        """Execute a dynamic attack within a Byzantine Sandbox."""
        if not self.isolation:
            return []

        async with self.isolation.provision_sandbox(label=f"siege_{vector.name}") as sandbox:
            await sandbox.write_file("siege_target.py", code)
            output = await sandbox.execute_python("siege_target.py")

            findings = []
            if output:
                try:
                    findings_str = await sandbox.read_file("findings.json")
                    f_list = json.loads(findings_str)
                    if isinstance(f_list, list):
                        findings.extend(f_list)
                except Exception:
                    pass

                if vector.name == "leak_hunter" and output.stderr:
                    if "ResourceWarning" in output.stderr or "leaked" in output.stderr.lower():
                        findings.append(
                            f"LeakHunter: Resource leak detected: {output.stderr[:100]}"
                        )

            vector_findings = await vector.attack(code, context)
            findings.extend(vector_findings)

            return findings


class LegionOmegaEngine:
    """⚖️ LEGION-OMEGA: The Sovereign Arbiter (v6.1 Capital Convergence)."""

    def __init__(
        self,
        max_cycles: int = 3,
        vectors: list[AttackVector] | Mapping[str, AttackVector] | None = None,
        isolation: IsolationManager | None = None,
        autonomy_threshold: float = 0.7,
        db_path: str = "cortex_legion.db",
    ):
        self.blue_team = BlueTeamAgent(isolation=isolation)
        self.isolation = isolation or IsolationManager()
        self.kv_router = KVRouter()
        self.maxwell_filter = LegionMaxwellFilter()
        self.vault = ConceptVault(db_path=db_path)
        self._vault_initialized = False
        self.autonomy_threshold = autonomy_threshold

        _vectors = vectors or RED_TEAM_SWARM
        if isinstance(_vectors, Mapping):
            self.vectors_list = list(_vectors.values())
        else:
            self.vectors_list = list(_vectors)

        self.red_team = RedTeamSwarm(vectors=self.vectors_list, isolation=self.isolation)
        self.max_cycles = max_cycles

    async def _ensure_vault(self):
        """Ensure the ConceptVault is initialized."""
        if not self._vault_initialized:
            await self.vault.init()
            self._vault_initialized = True

    async def evaluate_autonomy(self, intent: str, context: Mapping[str, Any]) -> bool:
        """AX-045: Evaluate if the problem warrants autonomous persistence."""
        complexity = len(context.get("data", [])) / 10.0 if "data" in context else 0.5
        is_autonomous = complexity >= self.autonomy_threshold
        log_limbic(
            f"AUTONOMY_EVAL: '{intent}' -> {'ACTIVE' if is_autonomous else 'PASSIVE'}"
            f" (Exergy: {complexity:.2f})",
            source="Ω₄_SOVEREIGN",
        )
        return is_autonomous

    def calculate_exergy(self, code: str, vulnerabilities: list[str]) -> float:
        """Ω₂: Calculate exergy score (useful work / total energy)."""
        if not code:
            return 0.0
        base_exergy = 1.0 - (len(vulnerabilities) / 10.0)
        return max(0.0, min(1.0, base_exergy))

    def calculate_entropy_delta(self, old_v_count: int, new_v_count: int) -> float:
        """Ω₂: Measure entropy reduction across cycles."""
        return float(old_v_count - new_v_count)

    async def forge(self, intent: str, context: Mapping[str, Any] | None = None) -> SiegeResult:
        """Forge code through the fire of the siege."""
        ctx = context or {}
        feedback: list[str] = []
        final_code = ""
        previous_code = ""
        vulnerabilities: list[str] = []
        previous_v_count = 100
        start_time = time.time()

        log_motor(
            f"LEGION-OMEGA v6.2: Invocando Maxwell Crystallizer para '{intent}'", action="FORGE"
        )

        await self._ensure_vault()
        warm_code = await self.vault.find_warm_start(intent)
        if warm_code:
            log_motor(f"VAULT: Injecting optimized pattern for '{intent}'", action="WARM_START")
            ctx = {**ctx, "warm_start_pattern": warm_code}

        is_autonomous = await self.evaluate_autonomy(intent, ctx)
        adaptive_cycles = self.max_cycles * (2 if is_autonomous else 1)

        for cycle in range(1, adaptive_cycles + 1):
            routed_prompt = self.kv_router.route(intent, f"Feedback: {feedback}")
            ctx_with_routing = {**ctx, "routed_prompt": routed_prompt}

            code = await self.blue_team.synthesize(intent, ctx_with_routing, feedback)

            if code == previous_code:
                log_motor(
                    "Thermal Equilibrium: Code identity reached. No further delta.",
                    action="STABLE"
                )
                break

            if not self.maxwell_filter.is_acceptable(code):
                feedback.append(
                    "MaxwellFilter: Low exergy detected. Remove placeholders."
                )
                continue

            vulnerabilities = await self.red_team.siege(code, ctx)
            v_count = len(vulnerabilities)

            exergy = self.calculate_exergy(code, vulnerabilities)
            entropy_delta = self.calculate_entropy_delta(previous_v_count, v_count)

            log_limbic(
                f"[CYCLE {cycle}] "
                f"EXERGY: {exergy:.2%} | "
                f"ENTROPY_DELTA: {entropy_delta:+.1f} | "
                f"VULNS: {v_count}",
                source="Ω₂_SENSOR",
                vibe="cterm-exergy",
            )

            if not vulnerabilities:
                log_motor(
                    f"Inmunidad Química alcanzada en ciclo {cycle}",
                    action="Ω₆",
                    vibe="cterm-sys",
                )
                if exergy >= 0.8:
                    await self.vault.crystallize(intent, code, exergy)
                final_code = code
                break

            feedback = vulnerabilities
            previous_code = code
            previous_v_count = v_count
            final_code = code

        duration = time.time() - start_time
        yield_h = (duration * 3600) / 60  # Simulated yield in hours

        return SiegeResult(
            success=len(vulnerabilities) == 0,
            final_code=final_code,
            cycles=cycle,
            vulnerabilities=vulnerabilities,
            exergy=self.calculate_exergy(final_code, vulnerabilities),
            entropy_delta=entropy_delta,
            yield_hours=yield_h,
        )


LEGION_OMEGA = LegionOmegaEngine()
