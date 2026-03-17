"""CORTEX Genesis — Declarative System Specification Models.

Dataclasses that define the shape of a system before it exists.
A SystemSpec is the DNA; GenesisResult is the birth certificate.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ComponentSpec:
    """A single component of a system to generate.

    Attributes:
        name: Component identifier (e.g. "store_mixin", "manager").
        component_type: One of "module", "dataclass", "mixin",
            "cli_command", "test", "config".
        imports: Explicit import lines this component needs.
        interfaces: Public method signatures to expose.
        dependencies: Names of other ComponentSpec this one depends on.
        template: Override template name (uses component_type default if None).
        docstring: Module-level docstring for the generated file.
    """

    name: str
    component_type: str = "module"
    imports: list[str] = field(default_factory=list)
    interfaces: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    template: Optional[str] = None
    docstring: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to plain dict."""
        return {
            "name": self.name,
            "component_type": self.component_type,
            "imports": list(self.imports),
            "interfaces": list(self.interfaces),
            "dependencies": list(self.dependencies),
            "template": self.template,
            "docstring": self.docstring,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ComponentSpec:
        """Deserialize from dict with strict schema validation."""
        allowed_keys = {
            "name",
            "component_type",
            "imports",
            "interfaces",
            "dependencies",
            "template",
            "docstring",
        }
        unknown_keys = set(d.keys()) - allowed_keys
        if unknown_keys:
            raise ValueError(f"Unknown keys in ComponentSpec: {unknown_keys}")

        return cls(
            name=str(d["name"]),
            component_type=str(d.get("component_type", "module")),
            imports=list(d.get("imports", [])),
            interfaces=list(d.get("interfaces", [])),
            dependencies=list(d.get("dependencies", [])),
            template=d.get("template"),
            docstring=str(d.get("docstring", "")),
        )


@dataclass
class SystemSpec:
    """Complete specification of a system to generate.

    This is the input contract for GenesisEngine.create().

    Attributes:
        name: System identifier (snake_case, e.g. "episodic_memory").
        description: Human-readable purpose.
        target_dir: Directory path where the system will be created.
        components: Ordered list of components to generate.
        system_type: One of "module", "skill", "agent", "workflow".
        auto_cli: Whether to generate CLI command stubs.
        auto_tests: Whether to generate test file stubs.
        tags: Metadata tags for CORTEX search.
    """

    name: str
    description: str = ""
    target_dir: str = ""
    components: list[ComponentSpec] = field(default_factory=list)
    system_type: str = "module"
    auto_cli: bool = False
    auto_tests: bool = False
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to plain dict."""
        return {
            "name": self.name,
            "description": self.description,
            "target_dir": self.target_dir,
            "components": [c.to_dict() for c in self.components],
            "system_type": self.system_type,
            "auto_cli": self.auto_cli,
            "auto_tests": self.auto_tests,
            "tags": list(self.tags),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> SystemSpec:
        """Deserialize from dict with strict schema validation."""
        allowed_keys = {
            "name",
            "description",
            "target_dir",
            "components",
            "system_type",
            "auto_cli",
            "auto_tests",
            "tags",
        }
        unknown_keys = set(d.keys()) - allowed_keys
        if unknown_keys:
            raise ValueError(f"Unknown keys in SystemSpec: {unknown_keys}")

        components = [ComponentSpec.from_dict(c) for c in d.get("components", [])]
        return cls(
            name=str(d["name"]),
            description=str(d.get("description", "")),
            target_dir=str(d.get("target_dir", "")),
            components=components,
            system_type=str(d.get("system_type", "module")),
            auto_cli=bool(d.get("auto_cli", False)),
            auto_tests=bool(d.get("auto_tests", False)),
            tags=list(d.get("tags", [])),
        )


@dataclass
class GenesisResult:
    """Output of a genesis operation.

    Attributes:
        spec: The original specification.
        files_created: Absolute paths of files successfully written.
        files_failed: Paths that could not be written (with reason).
        validation_passed: Whether post-creation validation succeeded.
        validation_errors: List of validation error messages.
        hours_saved: CHRONOS-1 yield calculation.
        created_at: ISO timestamp of creation.
    """

    spec: SystemSpec
    files_created: list[str] = field(default_factory=list)
    files_failed: list[str] = field(default_factory=list)
    validation_passed: bool = False
    validation_errors: list[str] = field(default_factory=list)
    hours_saved: float = 0.0
    created_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%S%z"))

    def summary(self) -> str:
        """One-line genesis summary."""
        status = "✅ PASSED" if self.validation_passed else "❌ FAILED"
        return (
            f"Genesis [{self.spec.name}]: {status} | "
            f"{len(self.files_created)} files | "
            f"CHRONOS-1: {self.hours_saved:.2f}h saved"
        )
