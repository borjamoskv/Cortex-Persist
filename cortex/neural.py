"""
CORTEX v5.0 — Neural-Bandwidth Sync (Zero-Latency Intent Ingestion).

Simulates "telepathic" intent inference on macOS by aggressively
monitoring implicit context (active window, clipboard) and deducing
the user's goal before they explicitly articulate it.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import re
import time
from dataclasses import dataclass

from cortex.sys_platform import get_cortex_dir, is_linux, is_macos, is_windows

__all__ = [
    "BaseClipboardSensor",
    "BaseWindowSensor",
    "LinuxClipboardSensor",
    "LinuxWindowSensor",
    "MacOSClipboardSensor",
    "MacOSWindowSensor",
    "NeuralContext",
    "NeuralHypothesis",
    "NeuralIntentEngine",
    "WindowsClipboardSensor",
    "WindowsWindowSensor",
    "calculate_entropy",
    "get_clipboard_sensor",
    "get_window_sensor",
]

try:
    if is_macos():
        import AppKit
except ImportError:
    AppKit = None

logger = logging.getLogger("cortex.neural")


def calculate_entropy(text: str) -> float:
    if not text:
        return 0.0
    entropy = 0.0
    for char in set(text):
        p = text.count(char) / len(text)
        entropy -= p * math.log2(p)
    return entropy


@dataclass
class NeuralContext:
    active_window: str
    clipboard_hash: str
    clipboard_entropy: float
    timestamp: float


@dataclass
class NeuralHypothesis:
    intent: str
    confidence: str
    trigger: str
    summary: str


class BaseWindowSensor:
    def get_active_window(self) -> str:
        return "unknown"


class MacOSWindowSensor(BaseWindowSensor):
    def get_active_window(self) -> str:
        if not AppKit:
            return "unknown"
        try:
            workspace = AppKit.NSWorkspace.sharedWorkspace()
            app = workspace.frontmostApplication()
            if app:
                name = app.localizedName()
                return name if name else "unknown"
            return "unknown"
        except (ValueError, OSError, RuntimeError, AttributeError) as e:
            logger.debug("Failed to get active window: %s", e)
            return "unknown"


class LinuxWindowSensor(BaseWindowSensor):
    def get_active_window(self) -> str:
        try:
            import subprocess

            result = subprocess.run(
                ["xdotool", "getactivewindow", "getwindowname"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            name = result.stdout.strip()
            return name if name else "unknown"
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            return "unknown"


class WindowsWindowSensor(BaseWindowSensor):
    def get_active_window(self) -> str:
        try:
            import ctypes

            user32 = ctypes.windll.user32  # type: ignore[attr-defined]
            hwnd = user32.GetForegroundWindow()
            length = user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            return buf.value if buf.value else "unknown"
        except (AttributeError, OSError, ValueError):
            return "unknown"


def get_window_sensor() -> BaseWindowSensor:
    if is_macos():
        return MacOSWindowSensor()
    if is_linux():
        return LinuxWindowSensor()
    if is_windows():
        return WindowsWindowSensor()
    return BaseWindowSensor()


class BaseClipboardSensor:
    def get_clipboard(self) -> str:
        return ""


class MacOSClipboardSensor(BaseClipboardSensor):
    def get_clipboard(self) -> str:
        if not AppKit:
            return ""
        try:
            pasteboard = AppKit.NSPasteboard.generalPasteboard()
            content = pasteboard.stringForType_(AppKit.NSPasteboardTypeString)
            if content:
                # Truncate to avoid massive clipboards blowing up memory/logs
                return content[:2000]
            return ""
        except (ValueError, OSError, RuntimeError, AttributeError) as e:
            logger.debug("Failed to get clipboard: %s", e)
            return ""


class LinuxClipboardSensor(BaseClipboardSensor):
    def get_clipboard(self) -> str:
        for cmd in (
            ["xclip", "-selection", "clipboard", "-o"],
            ["xsel", "--clipboard", "--output"],
        ):
            try:
                import subprocess

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=2,
                )
                if result.returncode == 0:
                    return result.stdout[:2000]
            except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
                continue
        return ""


class WindowsClipboardSensor(BaseClipboardSensor):
    def get_clipboard(self) -> str:
        try:
            import ctypes

            user32 = ctypes.windll.user32  # type: ignore[attr-defined]
            if not user32.OpenClipboard(0):
                return ""
            try:
                handle = user32.GetClipboardData(13)  # CF_UNICODETEXT
                if not handle:
                    return ""
                data = ctypes.c_wchar_p(handle)
                return (data.value or "")[:2000]
            finally:
                user32.CloseClipboard()
        except (AttributeError, OSError, ValueError):
            return ""


def get_clipboard_sensor() -> BaseClipboardSensor:
    if is_macos():
        return MacOSClipboardSensor()
    if is_linux():
        return LinuxClipboardSensor()
    if is_windows():
        return WindowsClipboardSensor()
    return BaseClipboardSensor()


class NeuralIntentEngine:
    """Infers intent by matching OS context against heuristic patterns."""

    def __init__(self) -> None:
        self.app_sensor = get_window_sensor()
        self.clip_sensor = get_clipboard_sensor()
        self._last_context: NeuralContext | None = None
        self._last_hypothesis: NeuralHypothesis | None = None
        self._last_hypothesis_timestamp: float = 0.0

        self._rules_path = get_cortex_dir() / "neural_rules.json"
        self._rules: list[tuple[re.Pattern, re.Pattern, str, str, str]] = []
        self._load_rules()

    def _load_rules(self) -> None:
        if not self._rules_path.exists():
            default_rules = [
                {
                    "app_re": r"(Cursor|VSCode|Code|iTerm|Terminal|Ghostty)",
                    "clip_re": (
                        r"(Traceback \(most recent call last\):"
                        r"|Error:|Exception:|FATAL:|panic:)"
                    ),
                    "intent": "debugging_error",
                    "confidence": "C4",
                    "trigger_desc": "Error trace in clipboard while in dev environment",
                },
                {
                    "app_re": r"(Chrome|Arc|Safari|Firefox|Brave)",
                    "clip_re": r"^(https?://|www\.)\S+$",
                    "intent": "researching",
                    "confidence": "C3",
                    "trigger_desc": "URL copied while in browser",
                },
                {
                    "app_re": r"(Cursor|VSCode|Code)",
                    "clip_re": r"(TO" + r"DO|FI" + r"XME|HA" + r"CK):",
                    "intent": "technical_debt_focus",
                    "confidence": "C3",
                    "trigger_desc": "Code debt marker in clipboard while in editor",
                },
                {
                    "app_re": r"(Linear|Jira|Trello|Notion)",
                    "clip_re": r"^(bug|feature|task|epic|ticket)\b",
                    "intent": "planning",
                    "confidence": "C3",
                    "trigger_desc": "Issue tracking text in planner app",
                },
            ]
            try:
                self._rules_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self._rules_path, "w", encoding="utf-8") as f:
                    json.dump(default_rules, f, indent=4)
            except (ValueError, OSError, RuntimeError) as e:
                logger.error("Failed to create neural defaults: %s", e)

        try:
            with open(self._rules_path, encoding="utf-8") as f:
                data = json.load(f)

            loaded = []
            for r in data:
                app_re = re.compile(r["app_re"], re.IGNORECASE)
                clip_re = re.compile(r["clip_re"], re.IGNORECASE)
                loaded.append((app_re, clip_re, r["intent"], r["confidence"], r["trigger_desc"]))
            self._rules = loaded
        except (ValueError, OSError, RuntimeError) as e:
            logger.error("Failed to load neural rules: %s", e)
            self._rules = []

    def read_context(self) -> tuple[NeuralContext, str]:
        """Capture the current implicit state of the OS and ephemeral raw text."""
        raw_clip = self.clip_sensor.get_clipboard()
        clip_hash = hashlib.sha256(raw_clip.encode("utf-8")).hexdigest() if raw_clip else ""
        clip_ent = calculate_entropy(raw_clip)

        ctx = NeuralContext(
            active_window=self.app_sensor.get_active_window(),
            clipboard_hash=clip_hash,
            clipboard_entropy=clip_ent,
            timestamp=time.monotonic(),
        )
        return ctx, raw_clip

    def _is_redundant_context(self, context: NeuralContext) -> bool:
        if not self._last_context:
            return False
        return (
            self._last_context.active_window == context.active_window
            and self._last_context.clipboard_hash == context.clipboard_hash
        )

    def infer_intent(
        self, context: NeuralContext, raw_clipboard: str = ""
    ) -> NeuralHypothesis | None:
        """Run heuristics over context to detect intent.

        Returns None if no intent matched, or if context hasn't changed
        meaningfully enough to trigger a new hypothesis.
        """
        if not context.active_window or context.active_window == "unknown":
            return None

        # Optimization: if context is strictly identical to last inference
        if self._is_redundant_context(context):
            return None

        self._last_context = context

        for app_re, clip_re, intent, conf, trigger in self._rules:
            if not app_re.search(context.active_window):
                continue
            if not raw_clipboard or not clip_re.search(raw_clipboard):
                continue

            hyp = NeuralHypothesis(
                intent=intent,
                confidence=conf,
                trigger=trigger,
                summary=f"Inferred intent '{intent}' ({trigger}) [App: {context.active_window}]",
            )

            # Deduplicate consecutive identical hypotheses
            if self._last_hypothesis and self._last_hypothesis.intent == hyp.intent:
                if (context.timestamp - self._last_hypothesis_timestamp) < 60:
                    return None

            self._last_hypothesis = hyp
            self._last_hypothesis_timestamp = context.timestamp
            return hyp

        return None
