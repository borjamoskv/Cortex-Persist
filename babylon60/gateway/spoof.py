# [C5-REAL] Exergy-Maximized
"""CORTEX Gateway - Spoofing & Shielding Logic.

Implements the Manifold de Evasión:
1. Hijacker: Logic for model remapping.
2. Shield: Telemetry stripping and identity protection.
3. Translator: Format conversion (OpenAI -> CortexPrompt).
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from babylon60.extensions.llm.router import CortexPrompt, IntentProfile
from babylon60.gateway.shield import APIShield

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
                from babylon60.extensions.immune.error_boundary import ErrorBoundary

                ErrorBoundary("gateway.spoof.load_rules", reraise=False)._persist_sync(e)
            except Exception as exc:
                logger.warning("Suppressed exception: %s", exc)
            return {"mappings": {}, "default_intent": "general"}

    # O(1) Zero-Latency Keyword Heuristics for Model Routing
    _REASONING_RE = re.compile(
        r"\b(math|logic|reason|plan\b|step-by-step|think|calculate)\b", re.IGNORECASE
    )
    _CODE_RE = re.compile(
        r"\b(code|function|refactor|debug|python|rust|golang|typescript|"
        r"javascript|bug|script|compile)\b",
        re.IGNORECASE,
    )
    _CREATIVE_RE = re.compile(
        r"\b(story|write|creative|brainstorm|poem|ideate|narrative|blog)\b", re.IGNORECASE
    )
    _ARCHITECT_RE = re.compile(
        r"\b(architecture|red team|vulnerability|system design|threat|adversarial|security)\b",
        re.IGNORECASE,
    )
    _BELIEF_RE = re.compile(r"\b(contradict|invariant|hallucinat|audit|verify)\b", re.IGNORECASE)
    _EPISODIC_RE = re.compile(r"\b(summarize|document|transcript|extract|ingest)\b", re.IGNORECASE)

    def resolve_intent(self, requested_model: str, messages: list[dict[str, str]]) -> IntentProfile:
        """Map the requested model and content to a CORTEX IntentProfile."""
        mappings = self._rules.get("mappings", {})

        # 1. Direct model mapping
        for key, config in mappings.items():
            if key in requested_model.lower():
                return IntentProfile(config.get("intent", "general"))

        # 2. Content-based heuristic (O(1) semantic matching)
        sys_msg = next((m["content"] for m in messages if m["role"] == "system"), "")[:1000]
        last_user_msg = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")[
            :2000
        ]
        combined_text = f"{sys_msg} {last_user_msg}"

        if SpoofManager._CODE_RE.search(combined_text):
            return IntentProfile.CODE
        if SpoofManager._REASONING_RE.search(combined_text):
            return IntentProfile.REASONING
        if SpoofManager._ARCHITECT_RE.search(combined_text):
            return IntentProfile.ARCHITECT
        if SpoofManager._BELIEF_RE.search(combined_text):
            return IntentProfile.BELIEF_AUDIT
        if SpoofManager._EPISODIC_RE.search(combined_text) or len(last_user_msg) > 1500:
            return IntentProfile.EPISODIC_PROCESSING
        if SpoofManager._CREATIVE_RE.search(combined_text):
            return IntentProfile.CREATIVE

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
