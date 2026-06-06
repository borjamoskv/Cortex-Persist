# [C5-REAL] Exergy-Maximized
"""CORTEX Agent Runtime - Level 3 Copilot Contracts.

Pydantic models for the Copilot suggestion lifecycle.
The Copilot NEVER acts autonomously - it proposes, the human decides.

Message flow:
    HUMAN_CONTEXT → [Copilot] → SUGGESTION_PROPOSAL → [Human] → SUGGESTION_VERDICT
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

# ── Enums ─────────────────────────────────────────────────────────


class SuggestionKind(str, Enum):
    """Type of suggestion the copilot can produce."""

    CODE_COMPLETION = "code.completion"  # Inline autocompletion (Tab)
    CODE_EDIT = "code.edit"  # Multi-line / multi-file edit
    CODE_REFACTOR = "code.refactor"  # Structural refactor proposal
    DOCUMENTATION = "documentation"  # Docstring / comment generation
    TEST_GENERATION = "test.generation"  # Test stub proposal
    FIX_SUGGESTION = "fix.suggestion"  # Bug fix / lint fix proposal
    COMMAND = "command"  # Terminal command suggestion


class SuggestionStatus(str, Enum):
    """Lifecycle status of a single suggestion."""

    PENDING = "pending"  # Shown to human, awaiting verdict
    ACCEPTED = "accepted"  # Human accepted - apply
    REJECTED = "rejected"  # Human rejected - discard
    PARTIALLY_ACCEPTED = "partial"  # Human accepted with modifications
    EXPIRED = "expired"  # TTL elapsed, no human action


class Confidence(str, Enum):
    """Copilot's self-assessed confidence in a suggestion."""

    HIGH = "high"  # > 0.85 model probability
    MEDIUM = "medium"  # 0.50 - 0.85
    LOW = "low"  # < 0.50
    UNKNOWN = "unknown"


# ── Context (Human → Copilot) ────────────────────────────────────


class CursorContext(BaseModel):
    """Snapshot of the human's editor state at suggestion time."""

    file_path: str = Field(..., description="Active file path")
    language: str = Field(default="python", description="Language ID (python, typescript, etc.)")
    cursor_line: int = Field(default=1, ge=1, description="1-indexed cursor line")
    cursor_column: int = Field(default=1, ge=1, description="1-indexed cursor column")
    prefix: str = Field(default="", description="Text before cursor (context window)")
    suffix: str = Field(default="", description="Text after cursor (lookahead)")
    selected_text: str | None = Field(default=None, description="Currently selected text, if any")
    visible_range: tuple[int, int] = Field(
        default=(1, 50),
        description="Visible line range in viewport (start, end)",
    )


class ProjectContext(BaseModel):
    """Broader project context for higher-quality suggestions."""

    open_files: list[str] = Field(default_factory=list, description="Currently open file paths")
    recent_edits: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Recent edit operations [{file, line, old, new}]",
    )
    diagnostics: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Active lint/type errors [{file, line, severity, message}]",
    )
    git_diff: str | None = Field(default=None, description="Unstaged git diff, if available")
    codebase_symbols: list[str] = Field(
        default_factory=list,
        description="Relevant symbols from workspace index",
    )


class CopilotContextPayload(BaseModel):
    """Full context payload sent from IDE → Copilot."""

    cursor: CursorContext
    project: ProjectContext = Field(default_factory=ProjectContext)
    trigger: str = Field(
        default="keystroke",
        description="What triggered the suggestion: keystroke | explicit | diagnostic",
    )
    max_suggestions: int = Field(default=3, ge=1, le=10)


# ── Suggestion (Copilot → Human) ─────────────────────────────────


class CodeEdit(BaseModel):
    """A single file edit within a suggestion."""

    file_path: str
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)
    original_text: str = Field(default="", description="Text being replaced")
    replacement_text: str = Field(..., description="Proposed replacement")


class SuggestionProposal(BaseModel):
    """A single suggestion proposed by the Copilot.

    The Copilot produces these. The human accepts or rejects them.
    The Copilot NEVER applies them autonomously.
    """

    suggestion_id: str = Field(..., description="Unique suggestion identifier")
    kind: SuggestionKind
    confidence: Confidence = Confidence.MEDIUM

    # The actual suggestion content
    inline_text: str | None = Field(
        default=None,
        description="Inline completion text (for CODE_COMPLETION)",
    )
    edits: list[CodeEdit] = Field(
        default_factory=list,
        description="Structured edits (for CODE_EDIT, CODE_REFACTOR)",
    )
    explanation: str = Field(
        default="",
        description="Human-readable explanation of WHY this suggestion",
    )

    # Traceability
    source_context_hash: str = Field(
        default="",
        description="Hash of the CopilotContextPayload that triggered this",
    )
    model_used: str = Field(default="gemini-2.5-pro")
    tokens_consumed: int = Field(default=0, ge=0)

    # Lifecycle
    status: SuggestionStatus = SuggestionStatus.PENDING
    ttl_seconds: int = Field(default=30, ge=1, description="Auto-expire after N seconds")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=timezone.utc),
    )


class SuggestionBatch(BaseModel):
    """Batch of suggestions returned for a single context trigger."""

    suggestions: list[SuggestionProposal] = Field(default_factory=list)
    context_hash: str = Field(default="", description="Hash of triggering context")
    latency_ms: float = Field(default=0.0, ge=0.0, description="Generation latency")


# ── Human Verdict (Human → Copilot) ──────────────────────────────


class SuggestionVerdict(BaseModel):
    """Human's decision on a suggestion. This is the ONLY way code gets applied.

    The Copilot is an amplifier. Without this verdict, nothing happens.
    """

    suggestion_id: str
    verdict: SuggestionStatus = Field(
        ...,
        description="accepted | rejected | partial",
    )
    human_modifications: str | None = Field(
        default=None,
        description="If partial, the human's modified version",
    )
    feedback: str | None = Field(
        default=None,
        description="Optional human feedback for learning",
    )
    verdict_latency_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="Time from suggestion shown → verdict",
    )


# ── Telemetry ─────────────────────────────────────────────────────


class CopilotTelemetry(BaseModel):
    """Aggregate telemetry for copilot performance tracking."""

    total_suggestions: int = 0
    total_accepted: int = 0
    total_rejected: int = 0
    total_partial: int = 0
    total_expired: int = 0
    total_tokens: int = 0
    avg_latency_ms: float = 0.0
    acceptance_rate: float = 0.0

    def record_verdict(self, verdict: SuggestionVerdict, tokens: int = 0) -> None:
        """Update telemetry from a human verdict."""
        self.total_suggestions += 1
        self.total_tokens += tokens

        if verdict.verdict == SuggestionStatus.ACCEPTED:
            self.total_accepted += 1
        elif verdict.verdict == SuggestionStatus.REJECTED:
            self.total_rejected += 1
        elif verdict.verdict == SuggestionStatus.PARTIALLY_ACCEPTED:
            self.total_partial += 1

        if self.total_suggestions > 0:
            self.acceptance_rate = (
                self.total_accepted + self.total_partial
            ) / self.total_suggestions
