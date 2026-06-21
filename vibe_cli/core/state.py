from dataclasses import dataclass, field
from typing import Dict, List, Any

@dataclass
class ProjectState:
    root_path: str

    files: List[str] = field(default_factory=list)
    stack: Dict[str, Any] = field(default_factory=dict)

    code_structure: Dict[str, Any] = field(default_factory=dict)
    dependency_graph: Dict[str, Any] = field(default_factory=dict)

    summaries: Dict[str, str] = field(default_factory=dict)
    features: List[Dict] = field(default_factory=list)
    conflicts: List[Dict] = field(default_factory=list)
    technical_debt: List[Dict] = field(default_factory=list)

    current_architecture: Dict[str, Any] = field(default_factory=dict)
    recommended_architecture: Dict[str, Any] = field(default_factory=dict)

    tasks: List[Dict] = field(default_factory=list)
