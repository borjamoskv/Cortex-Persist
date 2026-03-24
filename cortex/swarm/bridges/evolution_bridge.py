import logging
from pathlib import Path
from typing import Any

from cortex.engine import CortexEngine
from cortex.extensions.mejoralo.engine import MejoraloEngine
from cortex.extensions.mejoralo.models import ScanResult
from cortex.swarm.factory import SwarmFactory
from cortex.swarm.manager import SwarmManager

logger = logging.getLogger("cortex.swarm.bridges.evolution")

class EvolutionSwarmBridge:
    """
    Sovereign Evolution Bridge (Ω₄: Autonomy).
    
    Connects the MEJORAlo improvement engine with the Swarm recruitment factory
    to autonomously detect and resolve technical debt / architectural friction.
    """

    def __init__(
        self,
        engine: CortexEngine,
        mejoralo: MejoraloEngine,
        factory: SwarmFactory,
        manager: SwarmManager,
    ) -> None:
        self.engine = engine
        self.mejoralo = mejoralo
        self.factory = factory
        self.manager = manager
        self.ledger = manager.ledger

    async def evolve_project(
        self, 
        project_name: str, 
        path: str | Path, 
        threshold: int = 80,
        brutal: bool = False
    ) -> dict[str, Any]:
        """
        Execute an autonomous evolution cycle on a project.
        
        1. Scan for entropy (technical debt).
        2. Identify high-risk files.
        3. Recruit specialized optimization squads.
        4. Execute sharded refactoring.
        5. Verify results via Δ-Exergy.
        """
        root_path = Path(path).resolve()
        logger.info("EvolutionBridge: Starting Ω₄ cycle for %s at %s", project_name, root_path)

        # 1. Scan (Ω₃: Measure)
        scan_result: ScanResult = self.mejoralo.scan(project_name, root_path, brutal=brutal)
        score_before = scan_result.score
        
        if score_before >= 100 and not brutal:
            logger.info("EvolutionBridge: Project %s is already inmejorable (%d/100). skipping.", project_name, score_before)
            return {"status": "skipped", "score": score_before}

        # 2. Extract findings per file
        file_findings: dict[str, list[str]] = {}
        for dim in scan_result.dimensions:
            for finding in dim.findings:
                # Format: "path/to/file.py:line -> message"
                if " -> " in finding:
                    parts = finding.split(" -> ", 1)
                    location = parts[0]
                    if ":" in location:
                        file_path = location.split(":", 1)[0]
                        file_findings.setdefault(file_path, []).append(parts[1])

        if not file_findings:
            logger.info("EvolutionBridge: No actionable findings detected in %s.", project_name)
            return {"status": "no_findings", "score": score_before}

        # 3. Evolution Loop
        results = []
        for rel_file_path, findings in file_findings.items():
            abs_file_path = root_path / rel_file_path
            if not abs_file_path.exists():
                continue
            
            logger.info("EvolutionBridge: Evolving %s (Findings: %d)", rel_file_path, len(findings))
            
            # A. Recruit specialized squad for this file (Ω₃: Action)
            objective = f"Refactor and optimize {rel_file_path} to resolve: {', '.join(findings[:3])}"
            agent_ids = await self.factory.recruit_squad(objective, threshold=0.85)
            
            if not agent_ids:
                logger.warning("EvolutionBridge: Failed to recruit squad for %s", rel_file_path)
                continue

            # B. Shard refactoring task
            # The prompt includes the findings to guide the agents
            refactor_prompt = (
                f"Sovereign Refactoring Task (Ω₄):\n"
                f"File: {rel_file_path}\n"
                f"Problems to solve:\n- " + "\n- ".join(findings) + "\n\n"
                "Goal: Minimize entropy, eliminate code ghosts, and ensure 60fps/memory hygiene.\n"
                "Return the FULL optimized code content."
            )
            
            responses = await self.manager.shard_task(agent_ids, refactor_prompt)
            
            # C. Apply the best response (consensus-based if critical)
            # For simplicity in this bridge, we take the first successful response
            success_responses = [r for r in responses if r.status == "success"]
            if success_responses:
                best_code = success_responses[0].content
                # Write back (Ω₄: Mutation)
                abs_file_path.write_text(best_code)
                results.append({"file": rel_file_path, "status": "mutated"})
            else:
                results.append({"file": rel_file_path, "status": "failed"})

        # 4. Verification (Ω₃: Measurement)
        final_scan: ScanResult = self.mejoralo.scan(project_name, root_path)
        score_after = final_scan.score
        delta = score_after - score_before
        
        # 5. Ledger Audit (Ω₁)
        if self.ledger:
            self.ledger.record_transaction(
                project=project_name,
                action="evolution_cycle_complete",
                detail={
                    "score_before": score_before,
                    "score_after": score_after,
                    "delta": delta,
                    "files_affected": len(results),
                    "mechanical_justification": f"Ω₄ Evolution Cycle completed. Exergy boost: {delta} points."
                }
            )
            
        # Record session in Mejoralo Ledger
        self.mejoralo.record_session(
            project=project_name,
            score_before=score_before,
            score_after=score_after,
            actions=[f"Evolved {r['file']}: {r['status']}" for r in results]
        )

        return {
            "status": "completed",
            "score_before": score_before,
            "score_after": score_after,
            "delta": delta,
            "mutations": results
        }
