from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Literal, Optional, Protocol

TaskKind = Literal["reason", "retrieve", "plan", "execute", "audit", "summarize", "memory"]


@dataclass(slots=True)
class AgentCapability:
    name: str
    kinds: list[TaskKind]
    tags: list[str] = field(default_factory=list)
    priority: int = 0
    max_concurrent: int = 1


@dataclass(slots=True)
class SubagentRequest:
    task_id: str
    kind: TaskKind
    target_agent: str = ""
    prompt: str = ""
    context: dict[str, Any] = field(default_factory=dict)
    parent_task_id: Optional[str] = None
    timeout_ms: int = 30_000
    max_retries: int = 1
    require_capability: Optional[str] = None


@dataclass(slots=True)
class SubagentResponse:
    task_id: str
    ok: bool
    target_agent: str
    output: Any = None
    error: Optional[str] = None
    trace: dict[str, Any] = field(default_factory=dict)
    duration_ms: Optional[float] = None


class AgentHandler(Protocol):
    async def run(self, req: SubagentRequest) -> Any: ...


class AgentRegistry:
    def __init__(self) -> None:
        self._agents: dict[str, AgentCapability] = {}

    def register(self, cap: AgentCapability) -> None:
        self._agents[cap.name] = cap

    def get(self, name: str) -> AgentCapability | None:
        return self._agents.get(name)

    def all(self) -> list[AgentCapability]:
        return list(self._agents.values())

    def resolve(self, kind: TaskKind, require: str | None = None) -> str:
        candidates: list[AgentCapability] = []
        for agent in self._agents.values():
            if kind not in agent.kinds and kind not in agent.tags:
                continue
            if require and require not in {agent.name, *agent.kinds, *agent.tags}:
                continue
            candidates.append(agent)

        if not candidates:
            raise LookupError(f"No agent available for kind={kind!r}, require={require!r}")

        candidates.sort(key=lambda a: (a.priority, a.max_concurrent, a.name), reverse=True)
        return candidates[0].name


class SubagentRunner:
    def __init__(self, registry: AgentRegistry) -> None:
        self.registry = registry
        self._handlers: dict[str, AgentHandler] = {}
        self._locks: dict[str, asyncio.Semaphore] = {}

    def register_handler(self, name: str, handler: AgentHandler, max_concurrent: int = 1) -> None:
        self._handlers[name] = handler
        self._locks[name] = asyncio.Semaphore(max(1, max_concurrent))

    async def invoke_subagent(self, req: SubagentRequest) -> SubagentResponse:
        target = req.target_agent or self.registry.resolve(req.kind, req.require_capability)
        handler = self._handlers.get(target)
        if handler is None:
            return SubagentResponse(
                task_id=req.task_id,
                ok=False,
                target_agent=target,
                error=f"No handler registered for agent={target!r}",
            )

        lock = self._locks.get(target) or asyncio.Semaphore(1)
        last_error: str | None = None

        for attempt in range(req.max_retries + 1):
            t0 = time.monotonic()
            try:
                async with lock:
                    output = await asyncio.wait_for(handler.run(req), timeout=req.timeout_ms / 1000)
                return SubagentResponse(
                    task_id=req.task_id,
                    ok=True,
                    target_agent=target,
                    output=output,
                    duration_ms=(time.monotonic() - t0) * 1000,
                    trace={"attempt": attempt + 1},
                )
            except asyncio.TimeoutError:
                last_error = f"timeout after {req.timeout_ms}ms"
            except TimeoutError as e:
                last_error = f"timeout: {e}"
            except Exception as e:
                last_error = str(e)

        return SubagentResponse(
            task_id=req.task_id,
            ok=False,
            target_agent=target,
            error=last_error or "unknown error",
            trace={"attempts": req.max_retries + 1},
        )
