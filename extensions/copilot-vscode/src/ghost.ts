/**
 * CORTEX Copilot — Ghost Text Rendering
 *
 * Converts SuggestionProposals into VS Code InlineCompletionItems
 * (the "ghost text" that appears inline in the editor).
 *
 * Level 3 Contract: Ghost text is ALWAYS a proposal.
 * Tab = accept (human decision). Escape = reject (human decision).
 * The copilot NEVER applies text without human action.
 */

import * as vscode from "vscode";
import {
  SuggestionProposal,
  SuggestionStatus,
  SuggestionVerdict,
  CodeEdit,
} from "./types";
import { CopilotClient } from "./client";

/**
 * Render a single suggestion as ghost text (InlineCompletionItem).
 */
export function renderGhostText(
  suggestion: SuggestionProposal,
  position: vscode.Position
): vscode.InlineCompletionItem {
  const insertText = suggestion.inline_text ?? "";

  const item = new vscode.InlineCompletionItem(
    insertText,
    new vscode.Range(position, position)
  );

  // Command executed when human accepts (Tab)
  item.command = {
    command: "cortex-copilot.acceptSuggestion",
    title: "Accept CORTEX Suggestion",
    arguments: [suggestion.suggestion_id],
  };

  return item;
}

/**
 * Render multi-line/multi-file edit suggestions as ghost text items.
 */
export function renderMultiLineGhost(
  edits: CodeEdit[],
  suggestionId: string
): vscode.InlineCompletionItem[] {
  return edits.map((edit) => {
    const startPos = new vscode.Position(edit.start_line - 1, 0);
    const endPos = new vscode.Position(edit.end_line - 1, 0);

    const item = new vscode.InlineCompletionItem(
      edit.replacement_text,
      new vscode.Range(startPos, endPos)
    );

    item.command = {
      command: "cortex-copilot.acceptSuggestion",
      title: "Accept CORTEX Suggestion",
      arguments: [suggestionId],
    };

    return item;
  });
}

/**
 * Create an acceptance verdict (Tab pressed).
 */
export function createAcceptVerdict(
  suggestionId: string,
  shownAt: number
): SuggestionVerdict {
  return {
    suggestion_id: suggestionId,
    verdict: SuggestionStatus.ACCEPTED,
    human_modifications: null,
    feedback: null,
    verdict_latency_ms: Date.now() - shownAt,
  };
}

/**
 * Create a rejection verdict (Escape pressed or suggestion dismissed).
 */
export function createRejectVerdict(
  suggestionId: string,
  shownAt: number
): SuggestionVerdict {
  return {
    suggestion_id: suggestionId,
    verdict: SuggestionStatus.REJECTED,
    human_modifications: null,
    feedback: null,
    verdict_latency_ms: Date.now() - shownAt,
  };
}
