from __future__ import annotations

import hashlib
import re
from typing import Any

from .models import MembraneLog, MembraneLogLevel, PureEngram
from .sri_hash import auto_heal_html


class SovereignSanitizer:
    """
    SovereignSanitizer (The Digestive Engine)
    Implements Axiom Ω3 (Byzantine Default): Nothing is trusted by default.
    Purifies raw inputs before they reach the CORTEX persist layer.
    """

    # ReDoS-safe implementations (Eliminating catastrophic backtracking)
    EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,63}")
    PHONE_REGEX = re.compile(r"\b(?:\+?\d{1,3}[-. ]?)?\(?\d{3}\)?[-. ]?\d{3}[-. ]?\d{4}\b")

    # Matches local paths (macOS/Unix & Windows) securely
    LOCAL_PATH_REGEX = re.compile(r"(?:/(?:Users|home|var|tmp|etc)/[^\s]+)|(?:[A-Za-z]:\\[^\s]+)")

    # Matches typical traceback noise without catastrophic lookaheads
    TRACEBACK_REGEX = re.compile(
        r"Traceback\s*\(most\s*recent\s*call\s*last\):(?:[^\n]*\n){0,50}",
        re.IGNORECASE,
    )

    @classmethod
    def digest(cls, raw_engram: dict[str, Any]) -> tuple[PureEngram, MembraneLog]:
        """
        Takes an unverified dictionary representing an engram, sanitizes its contents,
        and returns a PureEngram with a cryptographic Audit Trail (MembraneLog).
        """
        # 1. Capture Original State
        raw_str = str(raw_engram)
        original_size = len(raw_str.encode("utf-8"))
        raw_hash = hashlib.sha256(raw_str.encode("utf-8")).hexdigest()

        log = MembraneLog(original_size_bytes=original_size)

        # 2. Sanitize Content
        content = raw_engram.get("content", "")

        # PII Stripping
        original_content = content
        content = cls.EMAIL_REGEX.sub("[PII_EMAIL_REDACTED]", content)
        content = cls.PHONE_REGEX.sub("[PII_PHONE_REDACTED]", content)
        if content != original_content:
            log.pii_stripped = True
            log.level = MembraneLogLevel.WARNING

        # Path Obfuscation
        original_content = content
        content = cls.LOCAL_PATH_REGEX.sub("[LOCAL_PATH_OBFUSCATED]", content)
        if content != original_content:
            log.paths_obfuscated = True

        # Traceback Pruning
        original_content = content
        content = cls.TRACEBACK_REGEX.sub("[TRACEBACK_PRUNED]", content)
        if content != original_content:
            log.tracebacks_pruned = True

        # SRI Healing (Alert #63 auto-remediation)
        if isinstance(content, str) and (
            "<script" in content.lower() or "<link" in content.lower()
        ):
            content = auto_heal_html(content)
        raw_engram["content"] = content

        # 3. Validation & Purity Seal
        try:
            # We construct the PureEngram. The Config(extra='forbid') will reject invalid fields.
            pure_engram = PureEngram(original_raw_hash=raw_hash, log=log, **raw_engram)
        except Exception:
            # INV-01 (Type Supremacy): Any incoming payload failing
            # validation will be automatically rejected.
            # We no longer convert this to an "error" engram; we block the write entirely.
            log.level = MembraneLogLevel.CRITICAL
            log.details = "Byzantine input rejected (INV-01 Type Supremacy violation)"
            raise ValueError(log.details) from None

        # Finalize log
        pure_str = pure_engram.model_dump_json()
        log.purified_size_bytes = len(pure_str.encode("utf-8"))

        # As per the plan, attach the log to the pure engram
        pure_engram.log = log

        return pure_engram, log
