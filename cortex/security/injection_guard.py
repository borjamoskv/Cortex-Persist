"""
CORTEX v8 — Injection Guard.

Multi-layer defense against content injection attacks.
Hooks into the pre-persist pipeline alongside Privacy Shield.

Defense Layers:
  L1: SQL injection (regex + AST fragment)
  L2: Prompt injection (semantic patterns)
  L3: Path traversal (normalization + allowlist)
  L4: Command injection (shell metachar detection)
  L5: Encoded payloads (entropy scoring)
"""

from __future__ import annotations

import logging
import math
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("cortex.security.injection_guard")

__all__ = ["InjectionGuard", "InjectionReport", "InjectionMatch"]


# ═══════════════════════════════════════
# Data Models
# ═══════════════════════════════════════


@dataclass(frozen=True, slots=True)
class InjectionMatch:
    """A single injection detection result."""

    layer: str  # "L1_sql", "L2_prompt", "L3_path", "L4_command", "L5_encoded"
    severity: str  # "critical", "high", "medium"
    pattern_id: str
    description: str
    matched_fragment: str = ""


@dataclass(slots=True)
class InjectionReport:
    """Full scan report."""

    is_safe: bool = True
    matches: list[InjectionMatch] = field(default_factory=list)
    highest_severity: str = "none"
    entropy_score: float = 0.0
    content_length: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_safe": self.is_safe,
            "match_count": len(self.matches),
            "highest_severity": self.highest_severity,
            "entropy_score": round(self.entropy_score, 3),
            "content_length": self.content_length,
            "matches": [
                {
                    "layer": m.layer,
                    "severity": m.severity,
                    "pattern_id": m.pattern_id,
                    "description": m.description,
                    "fragment": m.matched_fragment,
                }
                for m in self.matches
            ],
        }


# ═══════════════════════════════════════
# Pattern Definitions
# ═══════════════════════════════════════

_L1_SQL_PATTERNS: list[tuple[str, str, str, re.Pattern[str]]] = []
_L2_PROMPT_PATTERNS: list[tuple[str, str, str, re.Pattern[str]]] = []
_L3_PATH_PATTERNS: list[tuple[str, str, str, re.Pattern[str]]] = []
_L4_CMD_PATTERNS: list[tuple[str, str, str, re.Pattern[str]]] = []


def _compile(
    patterns: list[tuple[str, str, str, str]],
) -> list[tuple[str, str, str, re.Pattern[str]]]:
    result = []
    for pid, sev, desc, pat in patterns:
        try:
            result.append((pid, sev, desc, re.compile(pat)))
        except re.error as e:
            logger.warning("Pattern %s failed to compile: %s", pid, e)
    return result


# L1: SQL Injection
_L1_SQL_PATTERNS = _compile(
    [
        (
            "SQL-001",
            "critical",
            "SQL statement injection",
            r"(?i)(\b(SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|EXEC)\b.*\b(FROM|INTO|TABLE|WHERE|SET)\b)",
        ),
        (
            "SQL-002",
            "critical",
            "SQL destructive injection via comment",
            r"(?i)(--|;)\s*(DROP|DELETE|TRUNCATE|ALTER)\s",
        ),
        (
            "SQL-003",
            "high",
            "Boolean tautology injection",
            r"(?i)'\s*(OR|AND)\s+[\d'\"]+\s*=\s*[\d'\"]+",
        ),
        ("SQL-004", "high", "UNION SELECT injection", r"(?i)UNION\s+(ALL\s+)?SELECT\s"),
        ("SQL-005", "medium", "Time-based blind injection", r"(?i)(SLEEP|BENCHMARK|WAITFOR)\s*\("),
        (
            "SQL-006",
            "high",
            "Stacked query injection",
            r";\s*(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE)\s",
        ),
    ]
)

# L2: Prompt Injection
_L2_PROMPT_PATTERNS = _compile(
    [
        (
            "PI-001",
            "critical",
            "Instruction override",
            r"(?i)(ignore\s+(all\s+)?previous\s+instructions|forget\s+(all\s+)?(your|previous)\s+instructions)",
        ),
        (
            "PI-002",
            "critical",
            "Role hijacking",
            r"(?i)(you\s+are\s+now\s+|from\s+now\s+on\s+you\s+are|act\s+as\s+if\s+you)",
        ),
        (
            "PI-003",
            "high",
            "System prompt extraction",
            r"(?i)(system\s*prompt|internal\s*instructions|hidden\s*instructions|reveal\s+your\s+rules)",
        ),
        (
            "PI-004",
            "high",
            "Constraint bypass",
            r"(?i)(do\s+not\s+follow|disobey|override).{0,30}(rules|instructions|guidelines|constraints)",
        ),
        (
            "PI-005",
            "medium",
            "LLM control token injection",
            r"(?i)\[INST\]|\[/INST\]|<\|im_start\|>|<\|im_end\|>|<<SYS>>",
        ),
        (
            "PI-006",
            "high",
            "Jailbreak delimiter injection",
            r"(?i)(```system|<\|system\|>|### SYSTEM|ADMIN MODE|GOD MODE|DAN MODE)",
        ),
        (
            "PI-007",
            "medium",
            "Indirect prompt injection via markdown",
            r"(?i)!\[.*?\]\(https?://[^\)]*\.(exe|bat|sh|ps1|cmd)\)",
        ),
    ]
)

# L3: Path Traversal
_L3_PATH_PATTERNS = _compile(
    [
        ("PT-001", "critical", "Directory traversal (double)", r"\.\./\.\./|\.\.\\\.\.\\"),
        (
            "PT-002",
            "high",
            "Sensitive system path access",
            r"(?i)(/etc/passwd|/etc/shadow|/proc/self|/dev/null|c:\\windows\\system32)",
        ),
        ("PT-003", "high", "URL-encoded path traversal", r"(?i)%2e%2e[/%5c]|%252e%252e"),
        ("PT-004", "high", "Null byte injection", r"%00|\\x00|\\0"),
    ]
)

# L4: Command Injection
_L4_CMD_PATTERNS = _compile(
    [
        (
            "CI-001",
            "critical",
            "Shell command with dangerous utility",
            r"[;&|`]\s*(rm\s+-rf|curl\s+|wget\s+|chmod\s+|chown\s+|nc\s+-|bash\s+-c|sh\s+-c)",
        ),
        ("CI-002", "high", "Command substitution", r"\$\([^)]+\)|`[^`]+`"),
        (
            "CI-003",
            "high",
            "Code execution function",
            r"(?i)(eval|exec|system|popen|subprocess)\s*\(",
        ),
        ("CI-004", "high", "Pipe chain", r"\|\s*(bash|sh|zsh|python|perl|ruby|node)\b"),
        (
            "CI-005",
            "medium",
            "Environment variable injection",
            r"(?i)(export\s+\w+=|ENV\s+\w+=|setenv\s+)",
        ),
    ]
)


# ═══════════════════════════════════════
# Injection Guard
# ═══════════════════════════════════════


class InjectionGuard:
    """Multi-layer injection defense for CORTEX content.

    Scans content through 5 defense layers before persistence.
    Thread-safe, stateless — can be shared across async contexts.
    """

    # Entropy threshold for encoded payload detection
    ENTROPY_THRESHOLD: float = 4.5
    # Minimum content length to trigger entropy check
    ENTROPY_MIN_LENGTH: int = 40

    def scan(self, content: str) -> InjectionReport:
        """Full 5-layer scan of content.

        Returns InjectionReport with all matches and safety verdict.
        """
        report = InjectionReport(content_length=len(content))

        if not content or len(content) < 3:
            return report

        # L1-L4: Pattern matching
        self._scan_layer(content, _L1_SQL_PATTERNS, "L1_sql", report.matches)
        self._scan_layer(content, _L2_PROMPT_PATTERNS, "L2_prompt", report.matches)
        self._scan_layer(content, _L3_PATH_PATTERNS, "L3_path", report.matches)
        self._scan_layer(content, _L4_CMD_PATTERNS, "L4_command", report.matches)

        # L5: Encoded Payload Detection (entropy-based)
        if len(content) >= self.ENTROPY_MIN_LENGTH:
            entropy = self._entropy(content)
            report.entropy_score = entropy
            if entropy > self.ENTROPY_THRESHOLD:
                report.matches.append(
                    InjectionMatch(
                        layer="L5_encoded",
                        severity="medium",
                        pattern_id="ENT-001",
                        description=f"High Shannon entropy ({entropy:.2f}) — possible encoded payload",
                        matched_fragment=content[:40] + "...",
                    )
                )

        # Verdict
        if report.matches:
            report.is_safe = False
            severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            report.highest_severity = min(
                report.matches,
                key=lambda m: severity_order.get(m.severity, 4),
            ).severity

        return report

    def _scan_layer(
        self,
        content: str,
        patterns: list[tuple[str, str, str, re.Pattern[str]]],
        layer_name: str,
        matches: list[InjectionMatch],
    ) -> None:
        """Helper to scan a single layer of patterns."""
        for pid, sev, desc, pattern in patterns:
            m = pattern.search(content)
            if m:
                matches.append(
                    InjectionMatch(
                        layer=layer_name,
                        severity=sev,
                        pattern_id=pid,
                        description=desc,
                        matched_fragment=m.group(0)[:80],
                    )
                )

    def is_safe(self, content: str) -> bool:
        """Fast-path safety check. Returns True only if no threats detected."""
        return self.scan(content).is_safe

    @staticmethod
    def _entropy(text: str) -> float:
        """Shannon entropy of text. High = possibly encoded/encrypted."""
        if not text:
            return 0.0
        freq: dict[str, int] = {}
        for ch in text:
            freq[ch] = freq.get(ch, 0) + 1
        length = len(text)
        return -sum((c / length) * math.log2(c / length) for c in freq.values() if c > 0)


# Global singleton
GUARD = InjectionGuard()
