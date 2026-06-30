from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProjectState:
    root_path: str
    files: list[str] = field(default_factory=list)
    stack: dict[str, Any] = field(default_factory=dict)
    code_structure: dict[str, Any] = field(default_factory=dict)
    summaries: dict[str, str] = field(default_factory=dict)
    features: list[dict] = field(default_factory=list)
    conflicts: list[dict] = field(default_factory=list)
    technical_debt: list[dict] = field(default_factory=list)
    current_architecture: dict[str, Any] = field(default_factory=dict)
    recommended_architecture: dict[str, Any] = field(default_factory=dict)
    dependency_graph: dict[str, Any] = field(default_factory=dict)
    tasks: list[dict] = field(default_factory=list)
