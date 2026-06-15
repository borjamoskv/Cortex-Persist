from typing import Any
from schema.event_v1 import EventV1
from skills.registry import resolve
from dataclasses import dataclass

@dataclass
class ExecutionResult:
    artifact: dict[str, Any]

def run(event: EventV1) -> ExecutionResult:
    skill_class = resolve(event)
    skill_instance = skill_class()
    artifact = skill_instance.execute(event)
    return ExecutionResult(artifact=artifact)
