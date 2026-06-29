# [C5-REAL] Exergy-Maximized
"""Maxwell Router Agent - The Asymmetric Assessor.

Implements the Maxwell Demon logic to route tasks based on their Shannon entropy.
Hot (High Entropy) tasks are routed to the Boltzmann Engine (UltraThink).
Cold (Low Entropy) tasks are routed to Flash workers.
"""

import logging

from cortex.agents.base import BaseAgent
from cortex.agents.bus import MessageBus
from cortex.agents.manifest import AgentManifest
from cortex.agents.message_schema import AgentMessage, MessageKind, new_message
from cortex.agents.state import AgentStatus

logger = logging.getLogger("cortex.agents.maxwell_router")


class MaxwellRouterAgent(BaseAgent):
    """Router agent that classifies incoming tasks based on thermodynamic gradients.

    Evaluates the entropy of the task prompt. If it exceeds the threshold,
    it delegates to the BoltzmannEngine (Deep Reasoning). Otherwise, it delegates
    to standard Flash workers for exergy preservation.
    """

    def __init__(self, manifest: AgentManifest, bus: MessageBus, entropy_threshold: float = 0.8) -> None:
        super().__init__(manifest, bus)
        self.entropy_threshold = entropy_threshold

    def _calculate_shannon_entropy(self, text: str) -> float:
        """Heuristic calculation of semantic entropy.
        
        A real implementation would use LLM perplexity or token variance.
        For C5-REAL execution, we use a proxy based on task complexity keywords
        and length, normalized to [0, 1].
        """
        if not text:
            return 0.0
            
        high_entropy_keywords = {"refactor", "arquitectura", "diseño", "singularidad", "ultrathink", "bft"}
        text_lower = text.lower()
        
        # Base entropy from length
        entropy = min(len(text) / 2000.0, 0.5)
        
        # Spike entropy from keywords
        for keyword in high_entropy_keywords:
            if keyword in text_lower:
                entropy += 0.2
                
        return min(entropy, 1.0)

    async def _handle_message(self, message: AgentMessage) -> None:
        if message.kind != MessageKind.TASK_REQUEST:
            return

        prompt = message.payload.get("prompt", "")
        entropy = self._calculate_shannon_entropy(prompt)
        
        logger.info(f"[{self.manifest.agent_id}] Assessed task entropy: {entropy:.2f}")

        # Route based on Maxwell threshold
        if entropy >= self.entropy_threshold:
            target_agent = "boltzmann_engine_01"
            reason = "High entropy task. Routing to Boltzmann Engine (UltraThink)."
        else:
            target_agent = "flash_worker_01"
            reason = "Low entropy task. Routing to Flash Worker (T=0.0)."

        logger.info(f"[{self.manifest.agent_id}] Routing to {target_agent}: {reason}")

        # Emit delegated task
        delegation = new_message(
            sender=self.agent_id,
            recipient=target_agent,
            kind=MessageKind.TASK_REQUEST,
            payload=message.payload,
        )
        await self.bus.send(delegation)

        # Reply to original sender that routing is complete
        reply = new_message(
            sender=self.agent_id,
            recipient=message.sender,
            kind=MessageKind.TASK_RESULT,
            payload={
                "status": "routed",
                "target": target_agent,
                "entropy": entropy,
                "reason": reason
            },
            correlation_id=message.correlation_id
        )
        await self.bus.send(reply)

        self.state.status = AgentStatus.IDLE


def create_maxwell_router(name: str, bus: MessageBus, entropy_threshold: float = 0.8) -> MaxwellRouterAgent:
    """Factory for MaxwellRouterAgent."""
    manifest = AgentManifest(
        agent_id=name,
        
        purpose="Asymmetric task router based on Shannon entropy.",
        can_delegate=True
    )
    agent = MaxwellRouterAgent(manifest, bus, entropy_threshold)
    return agent
