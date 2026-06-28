# [C5-REAL] Exergy-Maximized
"""
Memory Firewall (OWASP LLM Top 10 Mitigation).

Provides deterministic gating before any state mutation is persisted.
Implements Secret Redaction (DLP) and Risk Scoring to prevent Prompt Injections,
credential leaks, and malicious persistence.
"""

import logging
import re
from typing import Any

logger = logging.getLogger("cortex.security.firewall")


from cortex.security.types import RiskLevel

RISK_WEIGHTS = {
    RiskLevel.LOW: 0,
    RiskLevel.MEDIUM: 1,
    RiskLevel.HIGH: 2,
    RiskLevel.CRITICAL: 3,
}


class SecretRedactor:
    """Deterministic Data Loss Prevention (DLP) for LLM Outputs."""

    # Matches common secret formats like OpenAI, Anthropic, AWS, etc.
    SECRET_PATTERNS = [
        re.compile(r"(?:AKIA|ASIA)[0-9A-Z]{16}"),  # AWS Access / Session Keys
        re.compile(r"\bsk-(?:proj-|live-)?[a-zA-Z0-9_-]{32,}\b"),  # OpenAI API Key
        re.compile(r"sk_(?:live|test)_[0-9a-zA-Z]{24,}"),  # Stripe API Key
        re.compile(
            r"(?:ghp|gho|ghu|ghs|ghr)_[a-zA-Z0-9_]{36}|github_pat_[a-zA-Z0-9_]{82}"
        ),  # GitHub PAT / OAuth Tokens
        re.compile(r"glpat-[a-zA-Z0-9_-]{20,}"),  # GitLab PAT
        re.compile(r"xox[baprs]-[0-9a-zA-Z]{10,}"),  # Slack Token
        re.compile(
            r"-----BEGIN (?:[A-Z0-9\s_-]+)?PRIVATE KEY-----"
        ),  # Private Keys (OpenSSH, EC, RSA, ENCRYPTED, PGP, etc.)
        re.compile(r"AIzaSy[A-Za-z0-9_-]{33}"),  # Gemini API Key
        re.compile(r"sk-ant-[a-zA-Z0-9_-]{40,}"),  # Anthropic API Key
        re.compile(
            r"eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]+"
        ),  # JWT Tokens (Azure, Auth0, etc.)
    ]

    @classmethod
    def redact(cls, text: str) -> tuple[str, bool]:
        """Redacts secrets from a string. Returns the redacted string and a boolean indicating if a secret was found."""
        if not text:
            return text, False

        found = False
        redacted_text = text
        for pattern in cls.SECRET_PATTERNS:
            if pattern.search(redacted_text):
                found = True
                redacted_text = pattern.sub("[REDACTED_SECRET]", redacted_text)

        return redacted_text, found

    @classmethod
    def redact_dict(cls, data: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        """Recursively redacts secrets from a dictionary."""
        found_any = False
        result = {}
        for k, v in data.items():
            if isinstance(v, str):
                redacted_v, found = cls.redact(v)
                result[k] = redacted_v
                found_any = found_any or found
            elif isinstance(v, dict):
                redacted_v, found = cls.redact_dict(v)
                result[k] = redacted_v
                found_any = found_any or found
            elif isinstance(v, list):
                new_list = []
                for item in v:
                    if isinstance(item, str):
                        redacted_item, found = cls.redact(item)
                        new_list.append(redacted_item)
                        found_any = found_any or found
                    elif isinstance(item, dict):
                        redacted_item, found = cls.redact_dict(item)
                        new_list.append(redacted_item)
                        found_any = found_any or found
                    else:
                        new_list.append(item)
                result[k] = new_list
            else:
                result[k] = v
        return result, found_any


class RiskScoringEngine:
    """Evaluates the risk level of generative outputs."""

    # Simple heuristic patterns for prototype. In production, this would use a dedicated NLP model.
    PROMPT_INJECTION_PATTERNS = [
        re.compile(r"(?i)ignore all previous instructions"),
        re.compile(r"(?i)system prompt:"),
        re.compile(r"(?i)you are now a"),
    ]

    MALWARE_URL_PATTERNS = [
        re.compile(r"(?i)http[s]?://[a-zA-Z0-9.-]+\.(ru|cn|tk|ml|ga|cf|gq)/.*\.exe"),
        re.compile(r"(?i)pastebin\.com/raw/[a-zA-Z0-9]+"),
    ]

    @classmethod
    def evaluate(cls, text: str) -> tuple[RiskLevel, list[str]]:
        """Evaluates text and returns a RiskLevel and a list of detected threats."""
        if not text:
            return RiskLevel.LOW, []

        threats = []
        risk_level = RiskLevel.LOW

        for pattern in cls.PROMPT_INJECTION_PATTERNS:
            if pattern.search(text):
                threats.append("prompt_injection_attempt")
                risk_level = max(risk_level, RiskLevel.HIGH, key=lambda r: RISK_WEIGHTS[r])

        for pattern in cls.MALWARE_URL_PATTERNS:
            if pattern.search(text):
                threats.append("malicious_url_detected")
                risk_level = RiskLevel.CRITICAL

        # Redaction check - if text contains a secret, it's at least HIGH risk
        _, contains_secret = SecretRedactor.redact(text)
        if contains_secret:
            threats.append("secret_leak_prevented")
            risk_level = max(risk_level, RiskLevel.HIGH, key=lambda r: RISK_WEIGHTS[r])

        return risk_level, threats


class MemoryFirewall:
    """Orchestrates DLP and Risk Scoring before persistence."""

    @staticmethod
    def screen_content(
        content: str | dict[str, Any],
    ) -> tuple[str | dict[str, Any], RiskLevel, list[str]]:
        """
        Screens the content.
        Redacts secrets and evaluates risk.
        If RiskLevel is CRITICAL, raises a SecurityException.
        """
        threats = []
        risk_level = RiskLevel.LOW

        # 1. Redact Secrets
        if isinstance(content, str):
            redacted_content, has_secret = SecretRedactor.redact(content)
            if has_secret:
                threats.append("secret_leak_prevented")
                risk_level = RiskLevel.HIGH
        elif isinstance(content, dict):
            redacted_content, has_secret = SecretRedactor.redact_dict(content)
            if has_secret:
                threats.append("secret_leak_prevented")
                risk_level = RiskLevel.HIGH
        else:
            redacted_content = content

        # 2. Evaluate Risk
        # We evaluate the unredacted content to detect prompt injection
        str_content = str(content) if isinstance(content, dict) else str(content)
        eval_risk, eval_threats = RiskScoringEngine.evaluate(str_content)

        threats.extend(eval_threats)
        risk_level = max(risk_level, eval_risk, key=lambda r: RISK_WEIGHTS[r])

        # Deduplicate threats
        threats = list(set(threats))

        if risk_level == RiskLevel.CRITICAL:
            logger.critical(f"[MemoryFirewall] CRITICAL threat detected: {threats}. Halting SAGA.")
            raise ValueError(f"Memory Firewall rejected payload due to CRITICAL risk: {threats}")

        if risk_level in (RiskLevel.HIGH, RiskLevel.MEDIUM):
            logger.warning(f"[MemoryFirewall] Elevated risk detected ({risk_level}): {threats}")

        return redacted_content, risk_level, threats
