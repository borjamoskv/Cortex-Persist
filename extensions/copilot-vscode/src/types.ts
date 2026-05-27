/**
 * CORTEX Copilot — VS Code Extension Types
 *
 * TypeScript interfaces mirroring the Python Pydantic models
 * from cortex/agents/copilot_contracts.py
 *
 * Level 3 Constraint: These types enforce the human-gated contract.
 * SuggestionProposal is ALWAYS a proposal. SuggestionVerdict is ALWAYS human.
 */

// ── Enums ────────────────────────────────────────────────────────

export enum SuggestionKind {
  CODE_COMPLETION = "code.completion",
  CODE_EDIT = "code.edit",
  CODE_REFACTOR = "code.refactor",
  DOCUMENTATION = "documentation",
  TEST_GENERATION = "test.generation",
  FIX_SUGGESTION = "fix.suggestion",
  COMMAND = "command",
}

export enum SuggestionStatus {
  PENDING = "pending",
  ACCEPTED = "accepted",
  REJECTED = "rejected",
  PARTIALLY_ACCEPTED = "partial",
  EXPIRED = "expired",
}

export enum Confidence {
  HIGH = "high",
  MEDIUM = "medium",
  LOW = "low",
  UNKNOWN = "unknown",
}

// ── Context (Editor → Backend) ───────────────────────────────────

export interface CursorContext {
  file_path: string;
  language: string;
  cursor_line: number;
  cursor_column: number;
  prefix: string;
  suffix: string;
  selected_text: string | null;
  visible_range: [number, number];
}

export interface ProjectContext {
  open_files: string[];
  recent_edits: Array<{
    file: string;
    line: number;
    old: string;
    new: string;
  }>;
  diagnostics: Array<{
    file: string;
    line: number;
    severity: string;
    message: string;
  }>;
  git_diff: string | null;
  codebase_symbols: string[];
}

export interface CopilotContextPayload {
  cursor: CursorContext;
  project: ProjectContext;
  trigger: "keystroke" | "explicit" | "diagnostic";
  max_suggestions: number;
}

// ── Suggestions (Backend → Editor) ───────────────────────────────

export interface CodeEdit {
  file_path: string;
  start_line: number;
  end_line: number;
  original_text: string;
  replacement_text: string;
}

export interface SuggestionProposal {
  suggestion_id: string;
  kind: SuggestionKind;
  confidence: Confidence;
  inline_text: string | null;
  edits: CodeEdit[];
  explanation: string;
  source_context_hash: string;
  model_used: string;
  tokens_consumed: number;
  status: SuggestionStatus;
  ttl_seconds: number;
  created_at: string;
}

export interface SuggestionBatch {
  suggestions: SuggestionProposal[];
  context_hash: string;
  latency_ms: number;
}

// ── Verdict (Editor → Backend) ───────────────────────────────────

export interface SuggestionVerdict {
  suggestion_id: string;
  verdict: SuggestionStatus;
  human_modifications: string | null;
  feedback: string | null;
  verdict_latency_ms: number;
}

// ── Telemetry ────────────────────────────────────────────────────

export interface CopilotTelemetry {
  total_suggestions: number;
  total_accepted: number;
  total_rejected: number;
  total_partial: number;
  total_expired: number;
  total_tokens: number;
  avg_latency_ms: number;
  acceptance_rate: number;
}

// ── WebSocket Protocol ───────────────────────────────────────────

export type ServerMessage =
  | { type: "suggestions"; payload: SuggestionBatch }
  | { type: "telemetry"; payload: CopilotTelemetry }
  | { type: "error"; message: string }
  | { type: "health"; status: string };

export type ClientMessage =
  | { type: "context"; payload: CopilotContextPayload }
  | { type: "verdict"; payload: SuggestionVerdict }
  | { type: "telemetry" }
  | { type: "health" };
