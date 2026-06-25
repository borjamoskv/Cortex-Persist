from __future__ import annotations

from typing import Any

from legacy_research.swarm.runtime import SubagentRequest


class MemoryHandler:
    def __init__(self, agent: Any | None = None, engine: Any | None = None) -> None:
        self.agent = agent
        self.engine = engine

    async def run(self, req: SubagentRequest) -> Any:
        op = req.context.get("op", "context")
        payload = {
            "content": req.prompt,
            "project_id": req.context.get("project_id", "default"),
            "fact_type": req.context.get("fact_type", "general"),
            "metadata": req.context.get("metadata"),
            "layer": req.context.get("layer", "semantic"),
            "query": req.context.get("query", req.prompt),
            "max_episodes": req.context.get("max_episodes", 5),
            "tenant_id": req.context.get("tenant_id"),
        }

        if self.agent is not None and hasattr(self.agent, "_dispatch"):
            return await self.agent._dispatch(op, payload)

        if self.engine is not None:
            if op == "store" and hasattr(self.engine, "store"):
                return await self.engine.store(
                    tenant_id=payload["tenant_id"],
                    project_id=payload["project_id"],
                    content=payload["content"],
                    fact_type=payload["fact_type"],
                    metadata=payload["metadata"],
                    layer=payload["layer"],
                )
            if op == "context" and hasattr(self.engine, "assemble_context"):
                return await self.engine.assemble_context(
                    tenant_id=payload["tenant_id"],
                    project_id=payload["project_id"],
                    query=payload["query"],
                    max_episodes=payload["max_episodes"],
                )
            if op == "status":
                return {"agent": "memory", "status": "ok", "bridge": "engine"}

        if op == "status":
            return {"agent": "memory", "status": "ok", "bridge": "noop"}

        raise RuntimeError(f"memory handler cannot execute op={op!r}")


class OracleHandler:
    def __init__(self, llm_manager: Any, system_prompt: str) -> None:
        self.llm_manager = llm_manager
        self.system_prompt = system_prompt

    async def run(self, req: SubagentRequest) -> Any:
        if not getattr(self.llm_manager, "available", False):
            raise RuntimeError("LLM core unavailable")

        target_url = req.context.get("target_url", "")
        depth = req.context.get("depth", 1)
        agent_type = req.context.get("agent_type", "ariadne")

        prompt = (
            f"## Target URL: {target_url}\n"
            f"## Requested Agent: {agent_type.upper()}\n"
            f"## Audit Depth: {depth}/3\n\n"
            "Generate a critical audit report for this target. Identify at least "
            "3 critical vulnerabilities or massive performance/growth bottlenecks. "
            "Provide actionable solutions."
        )

        return await self.llm_manager.complete(
            prompt=prompt,
            system=self.system_prompt,
            temperature=0.2,
            max_tokens=2048,
            intent="reasoning",
        )
