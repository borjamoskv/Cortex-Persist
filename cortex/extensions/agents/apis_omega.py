"""APIS-Ω — Sovereign Key Arbiter.

Manages the lifecycle, health, and acquisition of CORTEX LLM API keys.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger("cortex.extensions.agents.apis_omega")

SIGNUP_URLS = {
    "openai": "https://platform.openai.com/api-keys",
    "anthropic": "https://console.anthropic.com/settings/keys",
    "gemini": "https://aistudio.google.com/app/apikey",
    "groq": "https://console.groq.com/keys",
    "mistral": "https://console.mistral.ai/api-keys/",
    "deepseek": "https://platform.deepseek.com/api_keys",
    "perplexity": "https://www.perplexity.ai/settings/api",
    "xai": "https://console.x.ai/",
    "openrouter": "https://openrouter.ai/keys",
    "together": "https://api.together.xyz/settings/api-keys",
}


class ApisOmegaAgent:
    """Sovereign Agent for API Key Management."""

    def __init__(
        self,
        presets_path: str | Path = "/Users/borjafernandezangulo/30_CORTEX/config/llm_presets.json",
        db_path: str | Path | None = None,
    ):
        self.presets_path = Path(presets_path)
        self._engine: Any = None
        self._db_path = db_path
        self._agent_def: Any = None

    def _ensure_engine(self) -> None:
        if self._engine is not None:
            return
        from cortex.cli import get_engine
        from cortex.config import DEFAULT_DB_PATH

        db_val = str(self._db_path) if self._db_path else DEFAULT_DB_PATH
        self._engine = get_engine(db_val)

    def _load_agent_definition(self) -> None:
        if self._agent_def is not None:
            return
        try:
            from cortex.extensions.agents.registry import get_agent

            self._agent_def = get_agent("apis_omega")
        except ImportError:
            pass

    async def validate_key(self, provider: str, key: str, base_url: str) -> bool:
        """Lightweight check to verify if the key is actually functional."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # Standard OpenAI-compatible /models check
                headers = {"Authorization": f"Bearer {key}"}
                # Anthropic needs different headers
                if "anthropic" in provider.lower():
                    headers = {"x-api-key": key, "anthropic-version": "2023-06-01"}

                url = f"{base_url.rstrip('/')}/models"
                response = await client.get(url, headers=headers)
                return response.status_code == 200
        except Exception as e:
            logger.debug("Validation failed for %s: %s", provider, e)
            return False

    async def audit_keys(self, validate: bool = False) -> dict[str, Any]:
        """Check environment for required keys defined in presets."""
        with open(self.presets_path, encoding="utf-8") as f:
            presets = json.load(f)

        results = {
            "configured": [],
            "missing": [],
            "stats": {"total": 0, "coverage": 0.0, "valid_count": 0},
        }

        for provider, config in presets.items():
            tier = config.get("tier", "unknown")
            if tier == "local":
                continue

            env_key = config.get("env_key")
            if not env_key:
                continue

            results["stats"]["total"] += 1
            key_value = os.getenv(env_key)

            if key_value:
                provider_info = {
                    "provider": provider,
                    "env_key": env_key,
                    "tier": tier,
                    "status": "configured",
                }

                if validate:
                    is_valid = await self.validate_key(
                        provider, key_value, config.get("base_url", "")
                    )
                    provider_info["valid"] = is_valid
                    if is_valid:
                        results["stats"]["valid_count"] += 1

                results["configured"].append(provider_info)
            else:
                results["missing"].append(
                    {
                        "provider": provider,
                        "env_key": env_key,
                        "tier": tier,
                        "signup": SIGNUP_URLS.get(provider.lower(), ""),
                    }
                )

        total = results["stats"]["total"]
        if total > 0:
            results["stats"]["coverage"] = len(results["configured"]) / total

        return results

    async def pulse(self, validate: bool = True) -> str:
        """Execute a connectivity health check and report status."""
        self._ensure_engine()
        self._load_agent_definition()

        audit = await self.audit_keys(validate=validate)
        coverage = audit["stats"]["coverage"] * 100

        report = [
            "# 📡 APIS-Ω Connectivity Report",
            f"**Neural Coverage:** {coverage:.1f}%"
            f" ({len(audit['configured'])}/{audit['stats']['total']})",
            "",
        ]

        if audit["missing"]:
            report.append("## 🚨 Missing Neural Links")
            # Group by tier
            frontier_missing = [m for m in audit["missing"] if m["tier"] == "frontier"]
            if frontier_missing:
                report.append("### Frontier (CRITICAL)")
                for m in frontier_missing:
                    line = f"- **{m['provider'].upper()}** (`{m['env_key']}`)"
                    if m["signup"]:
                        line += f" [Get Key]({m['signup']})"
                    report.append(line)
                report.append("")

            other_missing = [m for m in audit["missing"] if m["tier"] != "frontier"]
            if other_missing:
                report.append("### Secondary Paths")
                for m in other_missing:
                    line = f"- {m['provider'].upper()}"
                    if m["signup"]:
                        line += f" [Get Key]({m['signup']})"
                    report.append(line)
                report.append("")

        if audit["configured"]:
            report.append("## ✅ Active Neural Paths")
            for c in audit["configured"]:
                status_icon = "🟢" if not validate or c.get("valid") else "🟡"
                report.append(f"- {status_icon} **{c['provider'].upper()}**")

        summary = "\n".join(report)

        # Persist to CORTEX
        await self._engine.store(
            project="SYSTEM",
            content=summary,
            fact_type="bridge",
            confidence="C5",
            source="agent:apis-omega",
            meta={
                "sub_type": "connectivity_audit",
                "coverage": coverage,
                "validated": validate,
                "valid_count": audit["stats"]["valid_count"],
            },
        )

        return summary


async def run_apis_cli():
    agent = ApisOmegaAgent()
    print(await agent.pulse(validate=True))


if __name__ == "__main__":
    asyncio.run(run_apis_cli())
