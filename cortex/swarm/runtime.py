from __future__ import annotations

import asyncio
import hashlib
import json
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Literal, Optional, Protocol

try:
    from opentelemetry import trace

    tracer = trace.get_tracer(__name__)
except ImportError:

    class DummySpan:
        def set_attribute(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    class DummyTracer:
        def start_as_current_span(self, *args, **kwargs):
            return DummySpan()

    tracer = DummyTracer()

TaskKind = Literal["reason", "retrieve", "plan", "execute", "audit", "summarize", "memory"]


@dataclass(slots=True)
class AgentCapability:
    name: str
    kinds: list[TaskKind]
    tags: list[str] = field(default_factory=list)
    priority: int = 0
    max_concurrent: int = 1
    meta: dict[str, Any] = field(default_factory=dict)
    agent_id: str = field(init=False)

    def __post_init__(self) -> None:
        cap_dict = {
            "name": self.name,
            "kinds": sorted(self.kinds),
            "tags": sorted(self.tags),
            "priority": self.priority,
            "max_concurrent": self.max_concurrent,
            "meta": dict(sorted(self.meta.items())),
        }
        payload = json.dumps(cap_dict, sort_keys=True).encode()
        self.agent_id = hashlib.sha256(payload).hexdigest()[:16]


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
        self._frozen: bool = False

    def freeze(self) -> None:
        self._frozen = True

    def register(self, cap: AgentCapability) -> None:
        if self._frozen:
            raise RuntimeError("Cannot register agents after registry is frozen")
        self._agents[cap.name] = cap

    def get(self, name: str) -> AgentCapability | None:
        return self._agents.get(name)

    def all(self) -> list[AgentCapability]:
        return list(self._agents.values())

    def get_candidates(self, kind: TaskKind, require: str | None = None) -> list[AgentCapability]:
        candidates: list[AgentCapability] = []
        for agent in self._agents.values():
            if kind not in agent.kinds and kind not in agent.tags:
                continue
            if require and require not in {agent.name, *agent.kinds, *agent.tags}:
                continue
            candidates.append(agent)
        return candidates

    def resolve(self, kind: TaskKind, require: str | None = None) -> str:
        candidates = self.get_candidates(kind, require)
        if not candidates:
            raise LookupError(f"No agent available for kind={kind!r}, require={require!r}")

        # Deterministic sorting if not using router directly
        candidates.sort(key=lambda a: getattr(a, "agent_id", a.name))
        return candidates[0].name


class SubagentRunner:
    def __init__(
        self,
        registry: AgentRegistry,
        audit_callback: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
    ) -> None:
        self.registry = registry
        self._handlers: dict[str, AgentHandler] = {}
        self._locks: dict[str, asyncio.Semaphore] = {}
        self.audit_callback = audit_callback

        from cortex.swarm.router import SwarmRouter

        self.router = SwarmRouter(registry)

    def register_handler(self, name: str, handler: AgentHandler, max_concurrent: int = 1) -> None:
        self._handlers[name] = handler
        self._locks[name] = asyncio.Semaphore(max(1, max_concurrent))

    async def invoke_subagent(self, req: SubagentRequest) -> SubagentResponse:
        if req.target_agent:
            target = req.target_agent
        elif self.router:
            req_dict = {
                "task": req.prompt or req.kind,
                "context": {
                    "task_id": req.task_id,
                    "kind": req.kind,
                    "require_capability": req.require_capability,
                },
            }
            decision = self.router.route(req_dict)
            selected_agents = decision.get("selected_agents", [])
            if not selected_agents:
                try:
                    target = self.registry.resolve(req.kind, req.require_capability)
                except LookupError as e:
                    return SubagentResponse(
                        task_id=req.task_id,
                        ok=False,
                        target_agent="",
                        error=str(e),
                    )
            else:
                target = selected_agents[0]
        else:
            target = self.registry.resolve(req.kind, req.require_capability)

        with tracer.start_as_current_span("swarm.dispatch") as span:
            span.set_attribute("swarm.task_id", req.task_id)
            span.set_attribute("swarm.target", target)
            span.set_attribute("swarm.kind", req.kind)

            if self.audit_callback:
                await self.audit_callback(
                    {
                        "task_id": req.task_id,
                        "target_agent": target,
                        "kind": req.kind,
                        "action": "SWARM_DISPATCH",
                        "status": "PENDING",
                    }
                )

            handler = self._handlers.get(target)
            if handler is None:
                err_msg = f"No handler registered for agent={target!r}"
                span.set_attribute("error", True)
                span.set_attribute("swarm.error", err_msg)
                if self.audit_callback:
                    await self.audit_callback(
                        {
                            "task_id": req.task_id,
                            "target_agent": target,
                            "action": "SWARM_DISPATCH",
                            "status": "ERROR",
                        }
                    )
                return SubagentResponse(
                    task_id=req.task_id,
                    ok=False,
                    target_agent=target,
                    error=err_msg,
                )

            lock = self._locks.get(target) or asyncio.Semaphore(1)
            last_error: str | None = None

            for attempt in range(req.max_retries + 1):
                t0 = time.monotonic()
                try:
                    async with lock:
                        output = await asyncio.wait_for(
                            handler.run(req), timeout=req.timeout_ms / 1000
                        )

                    if self.audit_callback:
                        await self.audit_callback(
                            {
                                "task_id": req.task_id,
                                "target_agent": target,
                                "action": "SWARM_DISPATCH",
                                "status": "SUCCESS",
                            }
                        )

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

            span.set_attribute("error", True)
            span.set_attribute("swarm.error", last_error or "unknown error")
            if self.audit_callback:
                await self.audit_callback(
                    {
                        "task_id": req.task_id,
                        "target_agent": target,
                        "action": "SWARM_DISPATCH",
                        "status": "ERROR",
                    }
                )

            return SubagentResponse(
                task_id=req.task_id,
                ok=False,
                target_agent=target,
                error=last_error or "unknown error",
                trace={"attempts": req.max_retries + 1},
            )
