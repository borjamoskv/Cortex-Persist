# [C5-REAL] Exergy-Maximized

import logging
from typing import Any

from legacy_research.agents.message_schema import AgentMessage, MessageKind, new_message
from legacy_research.sica.agent.stats import _LifetimeStats
from legacy_research.sica.meta_level import MetaJudgment

logger = logging.getLogger("cortex.sica.agent.emission")


class AgentEmitter:
    """Handles routing and formatting of outbound SICA messages."""

    def __init__(self, agent: Any, stats: _LifetimeStats):
        self.agent = agent
        self.stats = stats

    async def emit_result(
        self,
        original_msg: AgentMessage,
        task_id: str,
        result: dict[str, Any],
        judgment: MetaJudgment,
    ) -> None:
        """Emit a successful result with meta-annotations."""
        result["_sica_meta"] = {
            "genome_hash": self.agent._strategy.genome.genome_hash,
            "genome_generation": self.agent._strategy.genome.generation,
            "confidence": judgment.confidence,
            "mutations_applied": self.agent._strategy.genome.generation,
        }
        await self.agent.send_result(
            recipient=original_msg.sender,
            result=result,
            correlation_id=original_msg.correlation_id,
        )
        self.stats.tasks_succeeded += 1

    async def emit_failure(
        self,
        original_msg: AgentMessage,
        task_id: str,
        judgment: MetaJudgment | None,
    ) -> None:
        """Emit a task failure with diagnostic metadata."""
        payload = {
            "task_id": task_id,
            "error": judgment.diagnosis if judgment else "Unknown failure",
            "retryable": False,
            "_sica_meta": {
                "failure_class": judgment.failure_class.value
                if judgment and judgment.failure_class
                else None,
                "is_meta_failure": judgment.is_meta_failure if judgment else False,
                "genome_hash": self.agent._strategy.genome.genome_hash,
            },
        }
        msg = new_message(
            sender=self.agent.agent_id,
            recipient=original_msg.sender,
            kind=MessageKind.TASK_RESULT,
            payload=payload,
            correlation_id=original_msg.correlation_id or "auto",
        )
        await self.agent.bus.send(msg)
        self.stats.tasks_failed += 1

    async def emit_escalation(
        self,
        original_msg: AgentMessage,
        task_id: str,
        judgment: MetaJudgment,
    ) -> None:
        """Escalate to human/supervisor with full diagnostic context."""
        payload = {
            "task_id": task_id,
            "escalation": True,
            "diagnosis": judgment.diagnosis,
            "reasoning_chain": judgment.reasoning_chain,
            "introspection": self.agent._meta_level.introspect(),
        }
        msg = new_message(
            sender=self.agent.agent_id,
            recipient="supervisor",
            kind=MessageKind.TASK_RESULT,
            payload=payload,
            correlation_id=original_msg.correlation_id or "auto",
        )
        await self.agent.bus.send(msg)
        self.stats.escalations += 1

    async def emit_abort(
        self,
        original_msg: AgentMessage,
        task_id: str,
        judgment: MetaJudgment,
    ) -> None:
        """Emit constitutional abort - the nuclear option."""
        logger.error(
            "[%s] CONSTITUTIONAL ABORT: %s",
            self.agent.agent_id,
            judgment.diagnosis,
        )
        payload = {
            "task_id": task_id,
            "abort": True,
            "cardinal_violations": [
                str(v.principle)
                for v in (
                    judgment.constitutional_verdict.cardinal_violations
                    if judgment.constitutional_verdict
                    else []
                )
            ],
            "diagnosis": judgment.diagnosis,
        }
        msg = new_message(
            sender=self.agent.agent_id,
            recipient=original_msg.sender,
            kind=MessageKind.TASK_RESULT,
            payload=payload,
            correlation_id=original_msg.correlation_id or "auto",
        )
        await self.agent.bus.send(msg)
        self.stats.aborts += 1
