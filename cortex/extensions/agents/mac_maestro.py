"""
CORTEX - Mac Maestro Sovereign Agent v2.

Translates NL instructions into structured UIAction sequences
and executes them through the Mac-Maestro SDK Master Protocol.
Supports all four vectors: A (AppleScript), B (AX), C (KB), D (CG).
"""

from __future__ import annotations

import importlib
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any, Optional

from cortex.extensions.llm.manager import LLMManager
from cortex.extensions.llm.router import IntentProfile
from cortex.utils.applescript import run_applescript

logger = logging.getLogger("cortex.extensions.agents.mac_maestro")

# ── Common bundle-id aliases ──────────────────────────────────
_BUNDLE_ALIASES: dict[str, str] = {
    "finder": "com.apple.finder",
    "safari": "com.apple.Safari",
    "chrome": "com.google.Chrome",
    "firefox": "org.mozilla.firefox",
    "textedit": "com.apple.TextEdit",
    "notes": "com.apple.Notes",
    "terminal": "com.apple.Terminal",
    "music": "com.apple.Music",
    "mail": "com.apple.mail",
    "messages": "com.apple.MobileSMS",
    "calendar": "com.apple.iCal",
    "preview": "com.apple.Preview",
    "pages": "com.apple.iWork.Pages",
    "numbers": "com.apple.iWork.Numbers",
    "keynote": "com.apple.iWork.Keynote",
    "system preferences": "com.apple.systempreferences",
    "system settings": "com.apple.systempreferences",
    "xcode": "com.apple.dt.Xcode",
    "vscode": "com.microsoft.VSCode",
    "code": "com.microsoft.VSCode",
    "slack": "com.tinyspeck.slackmacgap",
    "discord": "com.hnc.Discord",
    "spotify": "com.spotify.client",
    "iterm": "com.googlecode.iterm2",
    "iterm2": "com.googlecode.iterm2",
    "arc": "company.thebrowser.Browser",
    "warp": "dev.warp.Warp-Stable",
}

# ── System Prompt ─────────────────────────────────────────────

SYSTEM_PROMPT = (
    "You are Mac Maestro, a sovereign macOS automation agent "
    "inside CORTEX.\n\n"
    "## Task\n"
    "Given a user instruction, produce a JSON execution plan.\n\n"
    "## Output Format\n"
    "Return ONLY a JSON object (no markdown):\n"
    "```json\n"
    "{\n"
    '  "bundle_id": "<bundle id>",\n'
    '  "app_name": "<human name>",\n'
    '  "explanation": "<1-line reasoning>",\n'
    '  "actions": [\n'
    "    {\n"
    '      "name": "<action name>",\n'
    '      "vector": "<A|B|C|D>",\n'
    '      "target_query": { ... },\n'
    '      "idempotent": true,\n'
    '      "retry_limit": 2,\n'
    '      "fallbacks": []\n'
    "    }\n"
    "  ]\n"
    "}\n"
    "```\n\n"
    "## Vectors\n"
    "- A (AppleScript): target_query has script/app_name/url\n"
    "- B (AXUIElement): target_query has role/title/id\n"
    "- C (Keyboard): target_query has text or keycode\n"
    "- D (CGEvent): target_query has x/y coords\n\n"
    "## Rules\n"
    "1. Prefer B for clicking UI elements.\n"
    "2. Use A for AppleScript or app activation.\n"
    "3. Use C for typing or key presses.\n"
    "4. Use D only for pixel-precise ops.\n"
    '5. Set "unsafe": true on destructive ops.\n'
    "6. bundle_id must be a real macOS identifier.\n"
)


class MacMaestroAgent:
    """NL instruction -> UIAction plan -> SDK execution."""

    def __init__(self) -> None:
        self.llm = LLMManager()

    async def execute(
        self, instruction: str,
    ) -> dict[str, Any]:
        """Full pipeline: LLM plan -> SDK orchestration."""
        if not self.llm.available:
            return {
                "success": False,
                "error": (
                    "No LLM provider configured. "
                    "Mac Maestro requires an active LLM."
                ),
            }

        logger.info("Mac Maestro v2 processing: %s", instruction)

        # Phase 1: LLM generates structured plan
        response = await self.llm.complete(
            prompt=instruction,
            system=SYSTEM_PROMPT,
            temperature=0.05,
            max_tokens=4096,
            intent=IntentProfile.CODE,
        )

        if not response:
            return {
                "success": False,
                "error": "LLM returned empty response.",
            }

        plan = self._parse_json_response(response)
        if not plan:
            return await self._legacy_fallback(
                instruction, response,
            )

        # Phase 2: Validate plan
        bundle_id = plan.get("bundle_id")
        actions_raw = plan.get("actions", [])
        explanation = plan.get(
            "explanation", "LLM-generated plan.",
        )

        if not bundle_id:
            app_name = plan.get("app_name", "").lower()
            bundle_id = _BUNDLE_ALIASES.get(app_name)
            if not bundle_id:
                return {
                    "success": False,
                    "error": (
                        f"Unknown app '{app_name}'. "
                        "Provide a valid bundle_id."
                    ),
                    "raw_plan": plan,
                }

        if not actions_raw:
            return {
                "success": False,
                "error": "Plan contains no actions.",
                "raw_plan": plan,
            }

        # Phase 3: Execute via SDK
        result = await self._execute_plan(
            bundle_id, actions_raw, explanation,
        )
        result["plan"] = plan
        return result

    # ── SDK Execution ─────────────────────────────────────────

    async def _execute_plan(
        self,
        bundle_id: str,
        actions_raw: list[dict[str, Any]],
        explanation: str,
    ) -> dict[str, Any]:
        """Run actions through MacMaestroWorkflow."""
        try:
            sdk_path = self._ensure_sdk_path()
            if sdk_path:
                sys.path.insert(0, sdk_path)

            from mac_maestro.models import UIAction
            from mac_maestro.workflow import MacMaestroWorkflow

            actions: list = []
            for raw in actions_raw:
                actions.append(self._build_action(raw, UIAction))

            wf = MacMaestroWorkflow(bundle_id)
            results = wf.run_sequence(
                actions,
                apply_safety_gate=True,
                abort_on_failure=False,
            )

            return {
                "success": all(results),
                "explanation": explanation,
                "bundle_id": bundle_id,
                "actions_executed": len(results),
                "action_results": results,
                "run_id": wf.run_id,
            }

        except ImportError:
            logger.warning(
                "SDK unavailable — AppleScript fallback.",
            )
            return await self._as_fallback(
                actions_raw, bundle_id, explanation,
            )

        except Exception as e:
            logger.exception("Execution failed: %s", e)
            return {
                "success": False,
                "error": str(e),
                "explanation": explanation,
                "bundle_id": bundle_id,
            }

    def _build_action(
        self, raw: dict[str, Any], UIActionCls: type,
    ) -> Any:
        """Convert JSON dict to UIAction dataclass."""
        fallbacks = []
        for fb in raw.get("fallbacks", []):
            fallbacks.append(UIActionCls(
                name=fb.get("name", "fallback"),
                vector=fb.get("vector", "A"),
                target_query=fb.get("target_query", {}),
                idempotent=fb.get("idempotent", True),
                retry_limit=fb.get("retry_limit", 1),
                unsafe=fb.get("unsafe", False),
            ))

        return UIActionCls(
            name=raw.get("name", "unnamed"),
            vector=raw.get("vector", "A"),
            target_query=raw.get("target_query", {}),
            idempotent=raw.get("idempotent", True),
            retry_limit=raw.get("retry_limit", 2),
            unsafe=raw.get("unsafe", False),
            fallbacks=fallbacks,
        )

    # ── Fallbacks ─────────────────────────────────────────────

    async def _as_fallback(
        self,
        actions_raw: list[dict[str, Any]],
        bundle_id: str,
        explanation: str,
    ) -> dict[str, Any]:
        """Run Vector A actions via osascript when SDK absent."""
        results: list[dict[str, Any]] = []
        ok = True

        for raw in actions_raw:
            tq = raw.get("target_query", {})
            if raw.get("vector") == "A":
                if "script" in tq:
                    s, out, err = await run_applescript(
                        tq["script"],
                    )
                elif "app_name" in tq:
                    name = tq["app_name"]
                    script = (
                        f'tell application "{name}" '
                        "to activate"
                    )
                    s, out, err = await run_applescript(script)
                else:
                    results.append({
                        "name": raw.get("name"),
                        "success": False,
                        "error": "No script in query.",
                    })
                    ok = False
                    continue

                results.append({
                    "name": raw.get("name"),
                    "success": s,
                    "stdout": out,
                    "stderr": err,
                })
                if not s:
                    ok = False
            else:
                results.append({
                    "name": raw.get("name"),
                    "success": False,
                    "error": (
                        f"Vector {raw.get('vector')} "
                        "needs SDK (unavailable)."
                    ),
                })
                ok = False

        return {
            "success": ok,
            "explanation": explanation,
            "bundle_id": bundle_id,
            "mode": "applescript_fallback",
            "action_results": results,
        }

    async def _legacy_fallback(
        self,
        instruction: str,
        raw_response: str,
    ) -> dict[str, Any]:
        """V1 compat: raw AppleScript from LLM."""
        data = self._parse_json_response(raw_response)
        if data and "script" in data:
            script = data["script"]
            expl = data.get("explanation", "Legacy.")
            s, out, err = await run_applescript(script)
            return {
                "success": s,
                "explanation": expl,
                "stdout": out,
                "stderr": err,
                "script": script,
                "mode": "legacy_v1",
            }

        return {
            "success": False,
            "error": (
                "Failed to parse plan. "
                f"Raw: {raw_response[:300]}"
            ),
        }

    # ── Utilities ─────────────────────────────────────────────

    def _ensure_sdk_path(self) -> Optional[str]:
        """Ensure mac_maestro SDK is importable."""
        if importlib.util.find_spec("mac_maestro"):
            return None
        candidates = [
            Path(__file__).resolve().parents[3] / "sdks",
            Path(__file__).resolve().parents[2] / "sdks",
        ]
        for c in candidates:
            init = c / "mac_maestro" / "__init__.py"
            if init.exists():
                return str(c)
        return None

    def _parse_json_response(
        self, text: str,
    ) -> Optional[dict[str, Any]]:
        """Multi-strategy JSON extraction."""
        # Strategy 1: direct parse
        try:
            r = json.loads(text.strip())
            if isinstance(r, dict):
                return r
        except json.JSONDecodeError:
            pass

        # Strategy 2: fenced code block
        m = re.search(
            r"```(?:json)?\s*(\{.*?\})\s*```",
            text,
            re.DOTALL,
        )
        if m:
            try:
                r = json.loads(m.group(1))
                if isinstance(r, dict):
                    return r
            except json.JSONDecodeError:
                pass

        # Strategy 3: outermost braces
        depth = 0
        start = None
        for i, ch in enumerate(text):
            if ch == "{":
                if depth == 0:
                    start = i
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0 and start is not None:
                    try:
                        r = json.loads(text[start:i + 1])
                        if isinstance(r, dict):
                            return r
                    except json.JSONDecodeError:
                        pass
                    start = None

        return None
