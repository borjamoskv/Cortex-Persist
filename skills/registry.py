from typing import Any, Callable, Dict, Type

class RegistryLockError(Exception):
    pass

_REGISTRY: Dict[str, Type] = {}

def register(skill_id: str, trigger_type: str = "command_received") -> Callable:
    def decorator(cls: Type) -> Type:
        _REGISTRY[skill_id] = cls
        return cls
    return decorator

def list_skills() -> list[str]:
    return list(_REGISTRY.keys())

def resolve(event: Any) -> Type:
    skill_class = _REGISTRY.get(event.skill_id)
    if not skill_class:
        raise KeyError(f"Skill {event.skill_id} not found")
    return skill_class
