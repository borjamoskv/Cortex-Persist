"""CORTEX Genesis Engine — A System That Creates Systems.

The core orchestrator that takes a SystemSpec and produces a complete,
validated subsystem: modules, tests, CLI commands, configs.

Axioms:
    Ω₀ (Self-Reference): Can generate its own specification via self_create().
    Ω₂ (Entropic Asymmetry): Every genesis reduces system entropy.
    Ω₃ (Byzantine Default): Validation before trust — all output is verified.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cortex.extensions.genesis.assembler import SystemAssembler
from cortex.extensions.genesis.models import ComponentSpec, GenesisResult, SystemSpec
from cortex.extensions.genesis.templates import TemplateRegistry
from cortex.extensions.genesis.validator import GenesisValidator

__all__ = ["GenesisEngine"]

logger = logging.getLogger("cortex.extensions.genesis.engine")


class GenesisEngine:
    """A system that creates systems.

    GenesisEngine is the recursive apex of CORTEX infrastructure.
    It takes a declarative SystemSpec and produces a complete, validated
    subsystem on disk — with deterministic, template-based code generation.

    No LLM inference is involved. Quality is guaranteed by construction.

    Usage::

        engine = GenesisEngine()
        spec = SystemSpec(
            name="my_system",
            components=[
                ComponentSpec(name="core", component_type="module"),
                ComponentSpec(name="models", component_type="dataclass"),
            ],
            auto_tests=True,
        )
        result = engine.create(spec)
        print(result.summary())
    """

    def __init__(self, cortex_root: Path | None = None) -> None:
        self.root = cortex_root or Path(__file__).parent.parent
        self.templates = TemplateRegistry()
        self.assembler = SystemAssembler(self.templates)
        self.validator = GenesisValidator()

    def create(self, spec: SystemSpec) -> GenesisResult:
        """Execute a full genesis: design → assemble → validate → measure.

        Args:
            spec: The system specification to materialize.

        Returns:
            GenesisResult with files created, validation status, and CHRONOS-1 yield.
        """
        logger.info("═" * 60)
        logger.info("GENESIS: Creating system '%s' (type=%s)", spec.name, spec.system_type)
        logger.info("═" * 60)

        # 1. Assemble files
        created, failed = self.assembler.assemble(spec, self.root)

        logger.info(
            "Assembly complete: %d files created, %d failed",
            len(created),
            len(failed),
        )

        # 2. Validate
        passed, errors = self.validator.validate(spec, created, self.root)

        # 3. Calculate CHRONOS-1 yield
        hours_saved = self._calculate_chronos(spec, created)

        # 4. Build result
        result = GenesisResult(
            spec=spec,
            files_created=created,
            files_failed=failed,
            validation_passed=passed,
            validation_errors=errors,
            hours_saved=hours_saved,
        )

        logger.info(result.summary())
        logger.info("═" * 60)

        # 5. Persist to CORTEX ledger
        self._persist_to_cortex(result)

        return result

    def extend(
        self,
        existing_dir: Path,
        new_components: list[ComponentSpec],
        *,
        auto_tests: bool = False,
    ) -> GenesisResult:
        """Add components to an existing system (incremental genesis).

        Unlike create(), this does NOT recreate the directory structure —
        it only adds new files for components that don't already exist.

        Args:
            existing_dir: Path to the existing system directory.
            new_components: Components to add.
            auto_tests: Whether to auto-generate test stubs for new components.

        Returns:
            GenesisResult with only the newly created files.
        """
        if not existing_dir.exists():
            raise FileNotFoundError(f"System directory not found: {existing_dir}")

        system_name = existing_dir.name
        logger.info(
            "GENESIS EXTEND: Adding %d components to '%s'",
            len(new_components),
            system_name,
        )

        spec = SystemSpec(
            name=system_name,
            system_type="module",
            auto_tests=auto_tests,
            components=new_components,
        )

        # Only render components whose files don't already exist
        created: list[str] = []
        failed: list[str] = []
        ordered = self.assembler._resolve_dependencies(new_components)

        for comp in ordered:
            template_name = comp.template or comp.component_type
            template = self.templates.get(template_name) or self.templates.get("module")
            if template is None:
                failed.append(f"{comp.name}: no template")
                continue

            rendered = template.render(system_name, comp)
            for rel_path_str, content in rendered.items():
                rel_path = Path(rel_path_str)
                # Guard against path traversal
                if ".." in rel_path.parts or rel_path.is_absolute():
                    logger.error("Path traversal blocked in extend: %s", rel_path)
                    failed.append(f"{comp.name}: Path traversal blocked {rel_path_str}")
                    continue

                file_path = existing_dir / rel_path
                if file_path.exists():
                    logger.info("SKIP (exists): %s", file_path)
                    continue
                try:
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    file_path.write_text(content, encoding="utf-8")
                    created.append(str(file_path))
                    logger.info("Created: %s", file_path)
                except OSError as e:
                    failed.append(f"{file_path}: {e}")

        # Auto-generate test stubs if requested
        if auto_tests:
            test_files = self.assembler._generate_test_stubs(spec, existing_dir.parent)
            created.extend(test_files)

        passed, errors = self.validator.validate(spec, created, existing_dir)
        hours_saved = self._calculate_chronos(spec, created)

        result = GenesisResult(
            spec=spec,
            files_created=created,
            files_failed=failed,
            validation_passed=passed,
            validation_errors=errors,
            hours_saved=hours_saved,
        )

        self._persist_to_cortex(result)
        return result

    def compose_templates(
        self,
        component_types: list[str],
        name: str,
        system_name: str,
        **kwargs: Any,
    ) -> dict[str, str]:
        """Compose multiple templates for a single component (#5).

        Renders the same component through multiple template renderers,
        collecting all output files. E.g. compose_templates(["module", "test"],
        "search", "memory") generates both search.py and test_search.py.

        Args:
            component_types: List of template names to chain.
            name: Component name.
            system_name: Parent system name.
            **kwargs: Extra ComponentSpec fields.

        Returns:
            Dict mapping relative path to rendered content.
        """
        comp = ComponentSpec(name=name, **kwargs)
        result: dict[str, str] = {}

        for tmpl_name in component_types:
            template = self.templates.get(tmpl_name)
            if template is None:
                logger.warning("compose: template '%s' not found, skipping", tmpl_name)
                continue
            rendered = template.render(system_name, comp)
            result.update(rendered)

        return result

    def create_from_dict(self, d: dict[str, Any]) -> GenesisResult:
        """Create a system from a raw dictionary (e.g. parsed YAML).

        Args:
            d: Dictionary matching SystemSpec.from_dict() schema.

        Returns:
            GenesisResult from the genesis operation.
        """
        spec = SystemSpec.from_dict(d)
        return self.create(spec)

    def self_create(self) -> SystemSpec:
        """Ω₀: Generate the specification of this very module.

        The Genesis Engine describes itself as a SystemSpec.
        This is the auto-referential proof: if the engine can
        spec itself, it can spec anything.

        Returns:
            SystemSpec that would recreate the genesis module.
        """
        return SystemSpec(
            name="genesis",
            description="A system that creates systems — the recursive apex of CORTEX.",
            target_dir="",
            system_type="module",
            auto_cli=True,
            auto_tests=True,
            tags=["meta", "genesis", "recursive", "sovereign"],
            components=[
                ComponentSpec(
                    name="models",
                    component_type="dataclass",
                    docstring="Declarative system specification models.",
                    interfaces=["SystemSpec", "ComponentSpec", "GenesisResult"],
                ),
                ComponentSpec(
                    name="templates",
                    component_type="module",
                    docstring="Deterministic template registry for code generation.",
                    interfaces=["register", "get", "list_templates"],
                    dependencies=["models"],
                ),
                ComponentSpec(
                    name="assembler",
                    component_type="module",
                    docstring="File assembler with topological dependency sort.",
                    interfaces=["assemble"],
                    dependencies=["models", "templates"],
                ),
                ComponentSpec(
                    name="validator",
                    component_type="module",
                    docstring="Post-creation structural validator.",
                    interfaces=["validate"],
                    dependencies=["models"],
                ),
                ComponentSpec(
                    name="engine",
                    component_type="module",
                    docstring="Core orchestrator — a system that creates systems.",
                    interfaces=["create", "create_from_dict", "self_create"],
                    dependencies=["models", "templates", "assembler", "validator"],
                ),
            ],
        )

    def preview(self, spec: SystemSpec) -> dict[str, list[str]]:
        """Preview what files would be created without writing anything.

        Args:
            spec: The system specification to preview.

        Returns:
            Dict mapping component name to list of filenames.
        """
        result: dict[str, list[str]] = {}
        ordered = self.assembler._resolve_dependencies(spec.components)

        for comp in ordered:
            template_name = comp.template or comp.component_type
            template = self.templates.get(template_name)
            if template is None:
                template = self.templates.get("module")
            if template is None:
                continue

            rendered = template.render(spec.name, comp)
            result[comp.name] = list(rendered.keys())

        # Add auto-generated files
        result["__auto__"] = ["__init__.py"]
        if spec.auto_tests:
            result["__auto__"].append("tests/")
        if spec.auto_cli:
            result["__auto__"].append(f"cli/{spec.name}_cmds.py")

        return result

    def _calculate_chronos(self, spec: SystemSpec, created: list[str]) -> float:
        """Calculate CHRONOS-1 yield for a genesis operation.

        Formula:
            Hours_Saved = ((files_touched × 6) + (codepaths_affected × 12)
                          + (validation_cost × 10)) × (complexity / 3) / 60

        Args:
            spec: The system specification.
            created: List of files actually created.

        Returns:
            Estimated hours saved (float).
        """
        files_touched = len(created)
        codepaths_affected = sum(len(c.interfaces) for c in spec.components)

        # Validation cost: 1 (trivial) to 5 (complex multi-system)
        validation_cost = min(5, max(1, len(spec.components)))

        # Complexity: based on dependency depth + system type
        complexity = min(5, max(1, self._estimate_complexity(spec)))

        hours = (
            ((files_touched * 6) + (codepaths_affected * 12) + (validation_cost * 10))
            * (complexity / 3)
            / 60
        )

        return round(hours, 2)

    def _estimate_complexity(self, spec: SystemSpec) -> int:
        """Estimate system complexity on a 1-5 scale.

        Based on:
        - Number of components
        - Dependency graph depth
        - System type
        """
        base = len(spec.components)

        # Dependency depth adds complexity
        max_depth = 0
        for comp in spec.components:
            depth = len(comp.dependencies)
            if depth > max_depth:
                max_depth = depth

        # System type multiplier
        type_weight = {
            "module": 1,
            "skill": 2,
            "agent": 3,
            "workflow": 1,
        }.get(spec.system_type, 1)

        score = base + max_depth + type_weight
        return min(5, max(1, int(math.log2(max(1, score)) + 1)))

    def _persist_to_cortex(self, result: GenesisResult) -> None:
        """Record a genesis event as a bridge in the CORTEX ledger (#2).

        Atomic: Genesis fails if persistence is unavailable.
        """
        from cortex.engine import CortexEngine

        engine = CortexEngine()
        engine.store_sync(
            content=(
                f"Genesis bridge: created system '{result.spec.name}' "
                f"({result.spec.system_type}) — "
                f"{len(result.files_created)} files, "
                f"CHRONOS-1: {result.hours_saved:.2f}h saved"
            ),
            fact_type="bridge",
            project="cortex",
            source="genesis-engine",
            tags=["genesis", "system_bridge", result.spec.system_type],
            confidence="C5",
            meta={
                "system_name": result.spec.name,
                "system_type": result.spec.system_type,
                "files_created": len(result.files_created),
                "hours_saved": result.hours_saved,
                "validation_passed": result.validation_passed,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        logger.info(
            "📦 Genesis persisted to CORTEX ledger: %s",
            result.spec.name,
        )
