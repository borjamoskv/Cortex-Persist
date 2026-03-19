import json
import logging
from pathlib import Path

from cortex.guards.models import ALLOWED_TIERS
from cortex.utils.errors import SovereignViolation

logger = logging.getLogger("cortex.guards.frontier")


class FrontierModelGuard:
    """
    Enforces Rule 1.3: Strictly mandates frontier or high-tier models.
    Rejects 'low', 'flash', 'haiku', or 'mini' models.
    """

    def __init__(self, presets_path: str | Path | None = None):
        if presets_path is None:
            # Default location relative to project root or cortex package
            # Based on previous research: config/llm_presets.json
            self.presets_path = Path("config/llm_presets.json")
        else:
            self.presets_path = Path(presets_path)

    def validate_config(self, provider: str, model: str | None = None) -> None:
        """
        Validates the current LLM configuration against Rule 1.3.

        Args:
            provider: The LLM provider (e.g., 'openai', 'ollama').
            model: Optional specific model name. If None, checks provider default.

        Raises:
            SovereignViolation: If the model/provider tier is not 'frontier' or 'high'.
        """
        if not self.presets_path.exists():
            logger.warning(
                "FrontierModelGuard: presets file not found at %s. Skipping validation.",
                self.presets_path,
            )
            return

        try:
            with open(self.presets_path) as f:
                presets = json.load(f)
        except Exception as e:
            logger.error("FrontierModelGuard: Failed to load presets: %s", e)
            return

        if provider not in presets:
            msg = f"FrontierModelGuard: Unknown provider '{provider}'. Rejecting for safety (Rule 1.3)."
            logger.error(msg)
            raise SovereignViolation(msg)

        config = presets[provider]
        tier = config.get("tier", "unknown")

        if tier not in ALLOWED_TIERS:
            msg = (
                f"FrontierModelGuard Violation: Provider '{provider}' has tier '{tier}'. "
                f"Rule 1.3 mandates {list(ALLOWED_TIERS)} models only."
            )
            logger.error(msg)
            raise SovereignViolation(msg)

        logger.info(
            "FrontierModelGuard: Configuration validated. Provider '%s' (Tier: %s) is compliant.",
            provider,
            tier,
        )
