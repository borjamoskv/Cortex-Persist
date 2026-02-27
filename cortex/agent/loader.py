"""CORTEX v6+ — YAML Agent Loader (role.yaml → CortexEngine).

Compiles a declarative YAML agent role into a fully configured
CORTEX agent with thermodynamic memory, ART Gate, BIFT routing,
sparse encoding, and session guardrails.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from cortex.agent.schema import AgentRole
from cortex.memory.frequency import BIFTRouter, ContinuousMemorySystem
from cortex.memory.guardrails import SessionGuardrail
from cortex.memory.resonance import AdaptiveResonanceGate
from cortex.memory.sparse import MushroomBodyEncoder
from cortex.memory.working import WorkingMemoryL1

logger = logging.getLogger("cortex.agent.loader")


class AgentInstance:
    """A fully hydrated CORTEX agent instance compiled from a role YAML.

    Contains all configured subsystems ready for execution.
    """

    __slots__ = (
        "role",
        "working_memory",
        "guardrail",
        "art_gate",
        "bift_router",
        "cms",
        "sparse_encoder",
        "_vector_store",
    )

    def __init__(
        self,
        role: AgentRole,
        working_memory: WorkingMemoryL1,
        guardrail: SessionGuardrail,
        art_gate: AdaptiveResonanceGate | None,
        bift_router: BIFTRouter,
        cms: ContinuousMemorySystem | None,
        sparse_encoder: MushroomBodyEncoder | None,
        vector_store: Any = None,
    ):
        self.role = role
        self.working_memory = working_memory
        self.guardrail = guardrail
        self.art_gate = art_gate
        self.bift_router = bift_router
        self.cms = cms
        self.sparse_encoder = sparse_encoder
        self._vector_store = vector_store

    @property
    def name(self) -> str:
        return self.role.name

    @property
    def model(self) -> str:
        return self.role.model

    @property
    def system_prompt(self) -> str:
        return self.role.system_prompt

    def status(self) -> dict[str, Any]:
        """Return a status snapshot of this agent instance."""
        return {
            "name": self.name,
            "model": self.model,
            "working_memory": repr(self.working_memory),
            "guardrail": self.guardrail.status(),
            "art_gate_enabled": self.art_gate is not None,
            "art_rho": self.role.memory.art_rho,
            "sparse_encoding": self.role.memory.sparse_encoding,
            "silent_engrams": self.role.memory.silent_engrams,
            "retrieval_band": self.role.memory.retrieval_band,
            "tools": self.role.tools,
        }


def load_agent(path: str | Path) -> AgentInstance:
    """Load and hydrate an agent from a role.yaml file.

    This is the main entry point for YAML → Agent compilation.
    """
    role = AgentRole.from_yaml_file(str(path))
    return compile_agent(role)


def compile_agent(role: AgentRole) -> AgentInstance:
    """Compile an AgentRole into a fully configured AgentInstance."""
    logger.info("Compiling agent '%s' (model=%s)", role.name, role.model)

    # 1. Working Memory (L1)
    wm = WorkingMemoryL1(max_tokens=role.memory.working_memory_tokens)

    # 2. Session Guardrail
    guardrail = SessionGuardrail(
        max_tokens=role.guardrails.max_session_tokens,
        warn_threshold=role.guardrails.warn_threshold,
        max_turns=role.guardrails.max_turns,
    )

    # 3. ART Gate (Strategy 2)
    art_gate = None
    # We'll wire the vector store later when engine is available
    # For now, create with None — caller can inject
    logger.debug("ART Gate configured with ρ=%.2f", role.memory.art_rho)

    # 4. BIFT Router (Strategy 5)
    bift_router = BIFTRouter()

    # 5. CMS (Strategy 1)
    cms = ContinuousMemorySystem(vector_store=None)

    # 6. Sparse Encoder (Strategy 3)
    sparse_encoder = None
    if role.memory.sparse_encoding:
        sparse_encoder = MushroomBodyEncoder(
            expansion_factor=4,
            sparsity=0.05,
        )
        logger.debug("Mushroom Body sparse encoding enabled (4x / 5%%)")

    agent = AgentInstance(
        role=role,
        working_memory=wm,
        guardrail=guardrail,
        art_gate=art_gate,
        bift_router=bift_router,
        cms=cms,
        sparse_encoder=sparse_encoder,
    )

    logger.info(
        "Agent '%s' compiled: L1=%d tokens, budget=%d tokens, tools=%s",
        role.name,
        role.memory.working_memory_tokens,
        role.guardrails.max_session_tokens,
        role.tools,
    )

    return agent
