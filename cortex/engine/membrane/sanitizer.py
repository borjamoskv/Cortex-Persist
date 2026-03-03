import hashlib
import re
from typing import Any

from .models import MembraneLog, MembraneLogLevel, PureEngram


class SovereignSanitizer:
    """
    SovereignSanitizer (The Digestive Engine)
    Implements Axiom Ω3 (Byzantine Default): Nothing is trusted by default.
    Purifies raw inputs before they reach the CORTEX persist layer.
    """

    # Simple regexes to ensure high performance (< 20ms write latency objective)
    # WARNING: These are basic implementations and might need refinement for production
    EMAIL_REGEX = re.compile(r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)")
    PHONE_REGEX = re.compile(r"(\+\d{1,2}\s?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}")

    # Matches local paths (macOS/Unix & Windows)
    LOCAL_PATH_REGEX = re.compile(r"(/(Users|home|var|tmp|etc)/[^\s]+)|([A-Z]:\\[^\s]+)")

    # Matches typical traceback noise
    TRACEBACK_REGEX = re.compile(
        r"Traceback\s*\(most\s*recent\s*call\s*last\):[\s\S]*?(?=\n[A-Za-z]+Error:|\Z)",
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

        raw_engram["content"] = content

        # 3. Validation & Purity Seal
        try:
            # We construct the PureEngram. The Config(extra='forbid') will reject invalid fields.
            pure_engram = PureEngram(original_raw_hash=raw_hash, **raw_engram)
        except Exception as e:
            # If the dict is severely malformed, we create an error engram instead of crashing
            # Axiom Ω5 (Antifragility): System requires stress as fuel.
            pure_engram = PureEngram(
                type="error",
                source="membrane",
                topic=raw_engram.get("topic", "system"),
                content=f"Engram digestion failed due to Byzantine input: {str(e)}",
                metadata={"raw_length": original_size},
                original_raw_hash=raw_hash,
            )
            log.level = MembraneLogLevel.CRITICAL
            log.details = "Byzantine input rejected and quarantined."

        # Finalize log
        pure_str = pure_engram.model_dump_json()
        log.purified_size_bytes = len(pure_str.encode("utf-8"))

        # As per the plan, attach the log to the pure engram
        pure_engram.log = log

        return pure_engram, log
