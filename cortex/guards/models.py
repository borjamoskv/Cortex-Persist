import logging
from dataclasses import dataclass

logger = logging.getLogger("cortex.guards.models")

# Binary names that indicate external oracle dependency
ORACLE_BINARIES: frozenset[str] = frozenset(
    {
        "kimi",
        "openai",
        "anthropic",
        "claude",
        "gpt",
        "gemini",
        "ollama",
        "llama-cli",
        "lm-studio",
    }
)

# Modules that enable process execution
EXEC_MODULES: frozenset[str] = frozenset(
    {
        "subprocess",
        "os",
        "shutil",
        "asyncio",
    }
)

# Sovereign fallback markers — if present, severity = WARNING
SOVEREIGN_MARKERS: frozenset[str] = frozenset(
    {
        "SovereignLLM",
        "ThoughtOrchestra",
        "CortexLLMRouter",
        "LLMProvider",
    }
)

# Rule 1.3 — Only frontier and high tier models are allowed
ALLOWED_TIERS: frozenset[str] = frozenset({"frontier", "high"})


@dataclass()
class DependencyViolation:
    """A detected Axiom 4 violation."""

    file: str
    line: int
    binary: str
    call_type: str
    has_fallback: bool = False

    @property
    def severity(self) -> str:
        """Determines if violation is a HARD fail or a WARNING."""
        return "WARNING" if self.has_fallback else "CRITICAL"

    def __str__(self) -> str:
        fallback_str = " (with fallback)" if self.has_fallback else ""
        return f"[{self.severity}] {self.file}:{self.line} — Found {self.call_type} to '{self.binary}'{fallback_str}"
