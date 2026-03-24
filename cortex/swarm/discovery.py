import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger("cortex.swarm.discovery")


class SkillMetadata(dict[str, Any]):
    """Parsed metadata from a SKILL.md manifest."""

    def __init__(self, data: dict[str, Any], path: Path) -> None:
        super().__init__(data)
        self.path = path
        self.name = data.get("name", path.parent.name)
        self.description = data.get("description", "")
        self.version = data.get("version", "0.0.0")
        self.category = data.get("category", "unspecified")
        self.trigger = data.get("trigger", "")
        self.aliases = data.get("aliases", [])


class SkillRegistry:
    """
    Sovereign Skill Discovery Engine (\u03a9\u2084).
    Dynamically scans and parses skills from the filesystem.
    """

    def __init__(self, base_path: Path | None = None) -> None:
        # Default to the standard CORTEX skills directory
        self.base_path = base_path or Path("~/.gemini/antigravity/skills").expanduser()
        self._skills: dict[str, SkillMetadata] = {}
        self._category_to_skills: dict[str, list[SkillMetadata]] = {}
        self.is_scanned: bool = False

    def scan(self) -> dict[str, SkillMetadata]:
        """Scan the base path for SKILL.md manifests and parse them (Synchronous)."""
        if not self.base_path.exists():
            logger.warning("SkillRegistry: Base path %s does not exist", self.base_path)
            return {}

        self._skills = {}
        self._category_to_skills = {}
        for skill_dir in self.base_path.iterdir():
            if not skill_dir.is_dir() or skill_dir.name.startswith((".", "_")):
                continue

            manifest_path = skill_dir / "SKILL.md"
            if manifest_path.exists():
                try:
                    metadata = self._parse_manifest(manifest_path)
                    self._register_skill(metadata)
                except Exception as e:
                    logger.error("SkillRegistry: Failed to parse %s: %s", manifest_path, e)

        logger.info("SkillRegistry: Discovered %d sovereign skills (sync)", len(self._skills))
        self.is_scanned = True
        return self._skills

    async def async_scan(self) -> dict[str, SkillMetadata]:
        """Scan the base path for SKILL.md manifests asynchronously (\u03a9\u2082)."""
        import anyio

        if not self.base_path.exists():
            logger.warning("SkillRegistry: Base path %s does not exist", self.base_path)
            return {}

        self._skills = {}
        self._category_to_skills = {}

        try:
            skill_dirs = await anyio.to_thread.run_sync(lambda: list(self.base_path.iterdir()))
        except Exception as e:
            logger.error("SkillRegistry: Failed to list directory %s: %s", self.base_path, e)
            return {}

        for skill_dir in skill_dirs:
            if not skill_dir.is_dir() or skill_dir.name.startswith((".", "_")):
                continue

            manifest_path = skill_dir / "SKILL.md"
            if await anyio.to_thread.run_sync(manifest_path.exists):
                try:
                    metadata = await self._async_parse_manifest(manifest_path)
                    self._register_skill(metadata)
                except Exception as e:
                    logger.error("SkillRegistry: Failed to parse %s: %s", manifest_path, e)

        logger.info("SkillRegistry: Discovered %d sovereign skills (async)", len(self._skills))
        return self._skills

    def _register_skill(self, metadata: SkillMetadata) -> None:
        """Internal helper to update indexes."""
        self._skills[metadata.name] = metadata
        cat = metadata.category or "unspecified"
        if cat not in self._category_to_skills:
            self._category_to_skills[cat] = []
        self._category_to_skills[cat].append(metadata)
        logger.debug("SkillRegistry: Registered skill '%s' [%s]", metadata.name, cat)

    async def _async_parse_manifest(self, path: Path) -> SkillMetadata:
        """Parse manifest metadata asynchronously."""
        import anyio
        content = await anyio.Path(path).read_text(encoding="utf-8")

        if content.startswith("---"):
            try:
                parts = content.split("---", 2)
                if len(parts) >= 3:
                     data = yaml.safe_load(parts[1])
                     return SkillMetadata(data, path)
            except (ValueError, yaml.YAMLError) as e:
                logger.warning("SkillRegistry: Malformed frontmatter in %s: %s", path, e)

        return SkillMetadata({"name": path.parent.name}, path)

    def _parse_manifest(self, path: Path) -> SkillMetadata:
        """Parse the YAML frontmatter from a SKILL.md file."""
        with open(path, encoding="utf-8") as f:
            content = f.read()

        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                data = yaml.safe_load(parts[1])
                return SkillMetadata(data, path)
        
        return SkillMetadata({"name": path.parent.name}, path)

    def get_skill(self, name: str) -> SkillMetadata | None:
        """Retrieve a specific skill by name."""
        return self._skills.get(name)

    def list_by_category(self, category: str) -> list[SkillMetadata]:
        """Filter discovered skills by category (O(1) lookup)."""
        return self._category_to_skills.get(category, [])

    @property
    def skills(self) -> dict[str, SkillMetadata]:
        return self._skills
