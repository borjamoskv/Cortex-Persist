import logging
import re
from typing import Any

from cortex.swarm.actuators.protocol import ActuatorProtocol, ActuatorResponse
from cortex.swarm.discovery import SkillMetadata

logger = logging.getLogger("cortex.swarm.actuators.skill")

_RESERVED_MANIFEST_KEYS = frozenset(
    {
        "name",
        "description",
        "version",
        "author",
        "license",
        "category",
        "classification",
        "danger_level",
        "created",
        "updated",
        "trigger",
        "aliases",
        "depends_on",
        "capabilities",
        "requires",
        "requirements",
        "tags",
        "composable_with",
        "incompatible_with",
        "amplifies",
        "amplified_by",
    }
)


def extract_canonical_metrics(skill: dict[str, Any]) -> list[tuple[str, Any]]:
    """Return scalar frontmatter KPI values that should execute as canonical outputs."""
    metrics: list[tuple[str, Any]] = []
    for key, value in skill.items():
        if key in _RESERVED_MANIFEST_KEYS:
            continue
        if not any(char.isupper() for char in key):
            continue
        if isinstance(value, (dict, list, tuple, set)):
            continue
        metrics.append((key, value))

    return metrics


def build_canonical_kpi_snapshot(
    skill: dict[str, Any], captured_at: str | None = None
) -> dict[str, Any]:
    """Build a canonical snapshot payload for a KPI skill."""
    from cortex.utils.canonical import now_iso

    metrics = extract_canonical_metrics(skill)
    if not metrics:
        raise ValueError("Skill does not expose canonical KPIs")

    resolved_at = captured_at or now_iso()
    metric_map = {metric_name: metric_value for metric_name, metric_value in metrics}
    content = f"Canonical KPI snapshot for skill '{skill['name']}' at {resolved_at}: " + "; ".join(
        f"{metric_name}={metric_value}" for metric_name, metric_value in metrics
    )
    return {
        "captured_at": resolved_at,
        "metrics": metric_map,
        "content": content,
    }


def extract_canonical_kpi_snapshot_record(
    fact: dict[str, Any],
    skill_name: str,
) -> dict[str, Any] | None:
    """Return a normalized KPI snapshot record if the fact belongs to the skill."""
    meta = fact.get("meta") or fact.get("metadata") or {}
    if not isinstance(meta, dict):
        return None

    metrics = meta.get("metrics")
    if meta.get("skill_name") != skill_name or not isinstance(metrics, dict) or not metrics:
        return None

    tags = fact.get("tags")
    normalized_tags = list(tags) if isinstance(tags, list) else []
    captured_at = meta.get("captured_at") or fact.get("created_at")
    created_at = fact.get("created_at") or captured_at
    if not isinstance(captured_at, str) or not isinstance(created_at, str):
        return None

    return {
        "fact_id": int(fact["id"]),
        "skill_name": skill_name,
        "project": str(fact["project"]),
        "fact_type": str(fact["fact_type"]),
        "source": str(fact.get("source") or ""),
        "content": str(fact.get("content") or ""),
        "tags": normalized_tags,
        "captured_at": captured_at,
        "created_at": created_at,
        "metrics": metrics,
    }


class SkillActuator(ActuatorProtocol):
    """
    Sovereign Skill Actuator.
    Executes local skill scripts or commands via the swarm.
    """

    def __init__(self, skill: SkillMetadata) -> None:
        self.skill = skill
        self._provider_id = f"skill:{skill.name}:{skill.version}"

    def _extract_canonical_metrics(self) -> list[tuple[str, Any]]:
        """Return frontmatter KPI values that should execute as canonical outputs."""
        return extract_canonical_metrics(self.skill)

    def _build_canonical_kpi_response(self) -> ActuatorResponse | None:
        """Return a direct KPI response for skills that expose fixed metric values."""
        metrics = self._extract_canonical_metrics()
        if not metrics:
            return None

        content = "\n".join(
            f"{metric_name}: {metric_value}" for metric_name, metric_value in metrics
        )
        return ActuatorResponse(
            content=content,
            metadata=self._build_kpi_metadata(metrics),
        )

    def _build_kpi_metadata(self, metrics: list[tuple[str, Any]]) -> dict[str, Any]:
        """Build metadata payload for single or multi-metric canonical skills."""
        metadata: dict[str, Any] = {
            "skill_name": self.skill.name,
            "version": self.skill.version,
            "category": self.skill.category,
            "trigger": self.skill.trigger,
            "mode": "canonical_kpi",
            "metrics": {metric_name: metric_value for metric_name, metric_value in metrics},
        }

        if len(metrics) == 1:
            metric_name, metric_value = metrics[0]
            normalized_name = re.sub(r"[^a-z0-9]+", "_", metric_name.lower()).strip("_")
            metadata["metric_name"] = metric_name
            metadata["metric_value"] = metric_value
            if normalized_name:
                metadata[normalized_name] = metric_value

        return metadata

    async def execute(
        self, task: str, context: dict[str, Any], task_id: str | None = None
    ) -> ActuatorResponse:
        """
        Execute a skill-based task.
        For now, this is a placeholder for real skill execution (Ω₄ phase 3).
        In the future, it would run `skill.trigger` or specific logic.
        """
        logger.info(
            "SkillActuator: Invoking skill '%s' for task %s",
            self.skill.name,
            task_id or "anon",
        )

        canonical_response = self._build_canonical_kpi_response()
        if canonical_response is not None:
            return canonical_response

        # Execute the skill's defined trigger mechanism as a subprocess
        trigger_cmd = self.skill.trigger
        if not trigger_cmd:
            logger.warning(
                "SkillActuator: Skill '%s' has no trigger. Returning stub.",
                self.skill.name,
            )
            return ActuatorResponse(
                content=f"Error: Skill '{self.skill.name}' has no trigger defined.",
                metadata={"status": "error", "skill_name": self.skill.name},
            )

        import asyncio
        import json
        import os

        env = os.environ.copy()
        env["CORTEX_TASK"] = task
        if context:
            try:
                env["CORTEX_CONTEXT"] = json.dumps(context)
            except Exception as e:
                logger.warning("SkillActuator: failed to serialize context: %s", e)

        cwd = self.skill.path.parent
        logger.debug("SkillActuator: Subprocess trigger '%s' in %s", trigger_cmd, cwd)

        try:
            process = await asyncio.create_subprocess_shell(
                trigger_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=env,
            )
            stdout, stderr = await process.communicate()

            content = stdout.decode("utf-8", errors="replace").strip()

            if process.returncode != 0:
                err_msg = stderr.decode("utf-8", errors="replace").strip()
                logger.error(
                    "SkillActuator: Skill '%s' failed (code %s): %s",
                    self.skill.name,
                    process.returncode,
                    err_msg,
                )
                if err_msg:
                    content += f"\n\n[STDERR]:\n{err_msg}"
                if not content:
                    content = f"Error: Command failed with code {process.returncode}"

            return ActuatorResponse(
                content=content or "No output produced.",
                metadata={
                    "skill_name": self.skill.name,
                    "version": self.skill.version,
                    "category": self.skill.category,
                    "trigger": trigger_cmd,
                    "returncode": process.returncode,
                    "status": "success" if process.returncode == 0 else "error",
                },
            )
        except Exception as e:
            logger.error("SkillActuator: Exception invoking skill '%s': %s", self.skill.name, e)
            return ActuatorResponse(
                content=f"Subprocess Exception: {e}",
                metadata={"status": "error", "skill_name": self.skill.name},
            )

    async def health_check(self) -> bool:
        """Verify the skill directory/manifest still exists."""
        return self.skill.path.exists()

    @property
    def provider_id(self) -> str:
        return self._provider_id
