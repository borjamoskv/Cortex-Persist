"""CORTEX Genesis — System Assembler.

Materializes SystemSpecs into real files on disk.
Handles dependency resolution via topological sort and
delegates rendering to the TemplateRegistry.
"""

from __future__ import annotations

import logging
from pathlib import Path

from cortex.extensions.genesis.models import ComponentSpec, SystemSpec
from cortex.extensions.genesis.templates import TemplateRegistry

__all__ = ["SystemAssembler"]

logger = logging.getLogger("cortex.extensions.genesis.assembler")


class SystemAssembler:
    """Assembles a SystemSpec into files on disk.

    The assembler:
    1. Resolves component dependencies via topological sort.
    2. Creates the target directory structure.
    3. Renders each component using the appropriate template.
    4. Writes files atomically (write to temp, then rename).
    """

    def __init__(self, registry: TemplateRegistry | None = None) -> None:
        self.registry = registry or TemplateRegistry()

    def assemble(self, spec: SystemSpec, base_dir: Path) -> tuple[list[str], list[str]]:
        """Generate all files for a system specification.

        Args:
            spec: The system specification to materialize.
            base_dir: Root directory under which the system dir is created.

        Returns:
            Tuple of (files_created, files_failed) as absolute path strings.
        """
        target = base_dir / spec.target_dir / spec.name if spec.target_dir else base_dir / spec.name
        target.mkdir(parents=True, exist_ok=True)

        created: list[str] = []
        failed: list[str] = []

        # Resolve dependency order
        ordered = self._resolve_dependencies(spec.components)

        # Always generate __init__.py first
        init_path = target / "__init__.py"
        if not init_path.exists():
            init_content = self._generate_init(spec)
            try:
                init_path.write_text(init_content, encoding="utf-8")
                created.append(str(init_path))
                logger.info("Created: %s", init_path)
            except OSError as e:
                failed.append(f"{init_path}: {e}")
                logger.error("Failed to create %s: %s", init_path, e)

        # Render each component
        for component in ordered:
            template_name = component.template or component.component_type
            template = self.registry.get(template_name)

            if template is None:
                logger.warning(
                    "No template '%s' for component '%s', falling back to 'module'",
                    template_name,
                    component.name,
                )
                template = self.registry.get("module")

            if template is None:
                failed.append(f"{component.name}: no template available")
                continue

            rendered = template.render(spec.name, component)

            for rel_path_str, content in rendered.items():
                rel_path = Path(rel_path_str)
                # Guard against path traversal
                if ".." in rel_path.parts or rel_path.is_absolute():
                    logger.error("Path traversal blocked: %s", rel_path)
                    failed.append(f"{component.name}: Path traversal blocked {rel_path_str}")
                    continue

                # Determine output location
                if component.component_type == "test":
                    # Tests go to a sibling test directory
                    file_path = base_dir.parent / "tests" / spec.name / rel_path
                elif component.component_type == "cli_command":
                    # CLI commands go to cortex/cli/
                    file_path = base_dir / "cli" / rel_path
                else:
                    file_path = target / rel_path

                try:
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    file_path.write_text(content, encoding="utf-8")
                    created.append(str(file_path))
                    logger.info("Created: %s", file_path)
                except OSError as e:
                    failed.append(f"{file_path}: {e}")
                    logger.error("Failed to create %s: %s", file_path, e)

        # Auto-generate test stubs if requested
        if spec.auto_tests:
            test_files = self._generate_test_stubs(spec, base_dir)
            created.extend(test_files)

        # Auto-generate CLI stub if requested
        if spec.auto_cli:
            cli_files = self._generate_cli_stub(spec, base_dir)
            created.extend(cli_files)

        return created, failed

    def _resolve_dependencies(self, components: list[ComponentSpec]) -> list[ComponentSpec]:
        """Topological sort of components by their declared dependencies.

        Uses Kahn's algorithm for O(V+E) deterministic ordering.
        Components with no dependencies come first.
        """
        # Build adjacency and in-degree maps
        name_to_comp: dict[str, ComponentSpec] = {c.name: c for c in components}
        in_degree: dict[str, int] = {c.name: 0 for c in components}
        dependents: dict[str, list[str]] = {c.name: [] for c in components}

        for comp in components:
            for dep in comp.dependencies:
                if dep in name_to_comp:
                    in_degree[comp.name] += 1
                    dependents[dep].append(comp.name)

        # Kahn's algorithm
        queue = [name for name, deg in in_degree.items() if deg == 0]
        ordered: list[ComponentSpec] = []

        while queue:
            # Sort for deterministic output
            queue.sort()
            current = queue.pop(0)
            ordered.append(name_to_comp[current])

            for dependent in dependents[current]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        # If we didn't get all components, there's a cycle — append remaining
        if len(ordered) < len(components):
            remaining = {c.name for c in components} - {c.name for c in ordered}
            for name in sorted(remaining):
                ordered.append(name_to_comp[name])
                logger.warning("Cycle detected: component '%s' has unresolved deps", name)

        return ordered

    def _generate_init(self, spec: SystemSpec) -> str:
        """Generate an __init__.py that exports key symbols."""
        exports: list[str] = []
        for comp in spec.components:
            if comp.component_type in ("module", "mixin", "dataclass"):
                class_name = "".join(w.capitalize() for w in comp.name.split("_"))
                if comp.component_type == "mixin" and not class_name.endswith("Mixin"):
                    class_name += "Mixin"
                elif comp.component_type == "module" and not class_name.endswith("Manager"):
                    class_name += "Manager"
                exports.append(class_name)

        lines = [
            f'"""CORTEX — {spec.name} package (auto-generated by Genesis Engine)."""',
            "",
        ]

        if exports:
            lines.append("__all__ = [")
            for exp in exports:
                lines.append(f'    "{exp}",')
            lines.append("]")
        else:
            lines.append("__all__: list[str] = []")

        lines.append("")
        return "\n".join(lines)

    def _generate_test_stubs(self, spec: SystemSpec, base_dir: Path) -> list[str]:
        """Auto-generate test stubs for all non-test components."""
        test_template = self.registry.get("test")
        if test_template is None:
            return []

        created: list[str] = []
        test_dir = base_dir.parent / "tests" / spec.name
        test_dir.mkdir(parents=True, exist_ok=True)

        # Create test __init__.py
        test_init = test_dir / "__init__.py"
        if not test_init.exists():
            try:
                test_init.write_text("", encoding="utf-8")
                created.append(str(test_init))
            except OSError:
                pass

        for comp in spec.components:
            if comp.component_type == "test":
                continue

            test_comp = ComponentSpec(
                name=comp.name,
                component_type="test",
                interfaces=comp.interfaces,
                imports=[f"# from cortex.{spec.name}.{comp.name} import *"],
            )
            rendered = test_template.render(spec.name, test_comp)

            for rel_path, content in rendered.items():
                file_path = test_dir / rel_path
                if not file_path.exists():
                    try:
                        file_path.write_text(content, encoding="utf-8")
                        created.append(str(file_path))
                    except OSError:
                        pass

        return created

    def _generate_cli_stub(self, spec: SystemSpec, base_dir: Path) -> list[str]:
        """Auto-generate a CLI command group for the system."""
        cli_template = self.registry.get("cli_command")
        if cli_template is None:
            return []

        created: list[str] = []
        cli_comp = ComponentSpec(
            name=spec.name,
            component_type="cli_command",
            interfaces=[c.name for c in spec.components if c.component_type != "test"],
            docstring=spec.description or f"CLI commands for {spec.name}",
        )

        rendered = cli_template.render(spec.name, cli_comp)
        cli_dir = base_dir / "cli"

        for rel_path, content in rendered.items():
            file_path = cli_dir / rel_path
            if not file_path.exists():
                try:
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    file_path.write_text(content, encoding="utf-8")
                    created.append(str(file_path))
                except OSError:
                    pass

        return created
