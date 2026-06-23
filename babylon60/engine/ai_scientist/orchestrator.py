import logging
from datetime import datetime, timezone
from typing import Any

from babylon60.audit.ledger import EnterpriseAuditLedger
from babylon60.auth.enterprise_identity import SovereignIdentity

from .analyst_writer import AnalystWriter
from .coder_executor import CoderExecutor
from .idea_generator import IdeaGenerator
from .reviewer import AdversarialReviewer

logger = logging.getLogger(__name__)

class AIScientistOrchestrator:
    """
    [C5-REAL] Exergy-Maximized Research Pipeline.
    Deterministic state mutation via causal DAG. Zero anergy state-machine.
    """

    def __init__(
        self,
        ledger: EnterpriseAuditLedger,
        identity: SovereignIdentity,
        idea_generator: IdeaGenerator,
        coder_executor: CoderExecutor,
        analyst_writer: AnalystWriter,
        reviewer: AdversarialReviewer,
    ):
        self.ledger = ledger
        self.identity = identity
        self.idea = idea_generator
        self.coder = coder_executor
        self.analyst = analyst_writer
        self.reviewer = reviewer

    async def _seal(self, action: str, resource: str, metadata: dict):
        """AX-045: Causal chain enforced. Cryptographic sign-off."""
        await self.ledger.log_action(
            tenant_id=self.identity.tenant_id,
            actor_role=self.identity.role,
            actor_id=self.identity.actor_id,
            action=f"AI_SCIENTIST_{action}",
            resource=resource,
            status="COMMITTED",
            metadata=metadata
        )

    async def run(self, topic: str, max_iterations: int = 3) -> dict[str, Any]:
        """Executes the pipeline as a deterministic forward-only DAG."""
        project_id = f"rsch_{datetime.now(timezone.utc).strftime('%y%m%d%H%M')}"
        await self._seal("START", project_id, {"topic": topic})

        state = {"topic": topic, "project_id": project_id, "iterations": 0}

        while state["iterations"] < max_iterations:
            state["idea"] = await self.idea.generate_novel_idea(topic)
            await self._seal("IDEA", state["idea"].get("title", "unknown"), {"score": state["idea"].get("novelty_score")})

            state["code"] = await self.coder.write_code(state["idea"])
            await self._seal("CODE", "code_bundle", {})

            state["results"] = await self.coder.execute_experiment(state["code"])
            await self._seal("EXEC", "experiment", state["results"].get("metrics", {}))

            state["draft"] = await self.analyst.write_paper(state["idea"], state["results"], state.get("feedback"))
            await self._seal("DRAFT", "pdf", {})

            review = await self.reviewer.conduct_review(state["draft"])
            await self._seal("REVIEW", "decision", {"score": review.get("score")})

            if review.get("accepted"):
                await self._seal("FINISH", project_id, {"iterations": state["iterations"]})
                return state

            state["feedback"] = review.get("feedback")
            state["iterations"] += 1
            logger.warning(f"[{project_id}] Rejected. Absorbing Adversarial Feedback. Iteration {state['iterations']}")

        raise RuntimeError(f"[{project_id}] Exergy exhausted. Max iterations reached without acceptance.")
