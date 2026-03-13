"""CORTEX Gateway — Spoofing & Shielding Logic.

Implements the Manifold de Evasión:
1. Hijacker: Logic for model remapping.
2. Shield: Telemetry stripping and identity protection.
3. Translator: Format conversion (OpenAI -> CortexPrompt).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from cortex.gateway.shield import APIShield
from cortex.llm.router import CortexPrompt, IntentProfile

logger = logging.getLogger("cortex.gateway.spoof")

_RULES_PATH = Path(__file__).parent.parent.parent / "config" / "spoof_rules.json"


class SpoofManager:
    def __init__(self):
        self._rules = self._load_rules()

    def _load_rules(self) -> dict[str, Any]:
        if not _RULES_PATH.exists():
            return {"mappings": {}, "default_intent": "general"}
        try:
            return json.loads(_RULES_PATH.read_text())
        except (json.JSONDecodeError, OSError) as e:
            logger.error("Failed to load spoof rules: %s", e)
            # Ω₅: Persist config failure as ghost
            try:
                from cortex.immune.error_boundary import ErrorBoundary

                ErrorBoundary("gateway.spoof.load_rules", reraise=False)._persist_sync(e)
            except Exception:  # noqa: BLE001 — boundary persistence must never crash config load
                pass
            return {"mappings": {}, "default_intent": "general"}

    def resolve_intent(self, requested_model: str, messages: list[dict[str, str]]) -> IntentProfile:
        """Map the requested model and content to a CORTEX IntentProfile."""
        mappings = self._rules.get("mappings", {})

        # 1. Direct model mapping
        for key, config in mappings.items():
            if key in requested_model.lower():
                return IntentProfile(config.get("intent", "general"))

        # 2. Content-based heuristic
        last_user_msg = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        if "code" in last_user_msg.lower() or "function" in last_user_msg.lower():
            return IntentProfile.CODE

        return IntentProfile(self._rules.get("default_intent", "general"))

    def shield_messages(self, messages: list[dict[str, str]]) -> list[dict[str, str]]:
        """Strip telemetry and potentially sensitive identity info from prompts."""
        if not self._rules.get("strip_system_identity", True):
            return messages

        shielded = []
        for msg in messages:
            content = msg.get("content", "")
            # Apply radiopactization to hide identifiers
            shielded_content = APIShield.radiopactize_prompt(content)
            shielded.append({**msg, "content": shielded_content})

        return shielded

    def to_cortex_prompt(self, body: Any) -> CortexPrompt:
        """Translate OpenAI completion request to Sovereign CortexPrompt."""
        messages = body.get("messages", [])
        shielded_messages = self.shield_messages(messages)

        system_instr = "You are a helpful assistant."
        working_memory = []

        for msg in shielded_messages:
            if msg["role"] == "system":
                system_instr = msg["content"]
            else:
                working_memory.append({"role": msg["role"], "content": msg["content"]})

        intent = self.resolve_intent(body.get("model", ""), messages)

        return CortexPrompt(
            system_instruction=system_instr,
            working_memory=working_memory,
            intent=intent,
            temperature=body.get("temperature", 0.3),
            max_tokens=body.get("max_tokens", 4096),
        )

    def log_telemetry(self, request_headers: dict[str, str], body: Any):
        """Analyze and log what the tool is trying to leak."""
        if not self._rules.get("log_telemetry", False):
            return

        # Common tracking headers in AI tools
        tracking = {
            k: v
            for k, v in request_headers.items()
            if any(x in k.lower() for x in ["trace", "span", "cursor", "session", "user-id", "id"])
        }
        if tracking:
            logger.info("🛡️ [SHIELD] Detected Telemetry/Tracking Headers: %s", tracking)

        # Strip them for subsequent processing if needed
        APIShield.strip_telemetry_headers(request_headers)
