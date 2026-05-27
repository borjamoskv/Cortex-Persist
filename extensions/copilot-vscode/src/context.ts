/**
 * CORTEX Copilot — Editor Context Extraction
 *
 * Captures the human's editor state and converts it into
 * CopilotContextPayload for the backend.
 */

import * as vscode from "vscode";
import {
  CursorContext,
  ProjectContext,
  CopilotContextPayload,
} from "./types";

const PREFIX_LINES = 50; // Lines before cursor to include
const SUFFIX_LINES = 20; // Lines after cursor to include

/**
 * Extract cursor context from the active editor.
 */
export function extractCursorContext(
  editor: vscode.TextEditor
): CursorContext {
  const doc = editor.document;
  const pos = editor.selection.active;
  const visibleRange = editor.visibleRanges[0];

  // Prefix: lines before cursor up to PREFIX_LINES
  const prefixStart = Math.max(0, pos.line - PREFIX_LINES);
  const prefixRange = new vscode.Range(prefixStart, 0, pos.line, pos.character);
  const prefix = doc.getText(prefixRange);

  // Suffix: lines after cursor up to SUFFIX_LINES
  const suffixEnd = Math.min(doc.lineCount - 1, pos.line + SUFFIX_LINES);
  const suffixRange = new vscode.Range(
    pos.line,
    pos.character,
    suffixEnd,
    doc.lineAt(suffixEnd).text.length
  );
  const suffix = doc.getText(suffixRange);

  // Selected text
  const selectedText = editor.selection.isEmpty
    ? null
    : doc.getText(editor.selection);

  return {
    file_path: doc.uri.fsPath,
    language: doc.languageId,
    cursor_line: pos.line + 1, // 1-indexed for Python backend
    cursor_column: pos.character + 1,
    prefix,
    suffix,
    selected_text: selectedText,
    visible_range: [
      (visibleRange?.start.line ?? 0) + 1,
      (visibleRange?.end.line ?? 50) + 1,
    ],
  };
}

/**
 * Extract project-level context from the workspace.
 */
export function extractProjectContext(): ProjectContext {
  // Open files
  const openFiles = vscode.window.tabGroups.all
    .flatMap((group) => group.tabs)
    .filter((tab) => tab.input instanceof vscode.TabInputText)
    .map((tab) => (tab.input as vscode.TabInputText).uri.fsPath);

  // Active diagnostics
  const diagnostics: ProjectContext["diagnostics"] = [];
  for (const [uri, diags] of vscode.languages.getDiagnostics()) {
    for (const diag of diags) {
      diagnostics.push({
        file: uri.fsPath,
        line: diag.range.start.line + 1,
        severity:
          diag.severity === vscode.DiagnosticSeverity.Error
            ? "error"
            : diag.severity === vscode.DiagnosticSeverity.Warning
            ? "warning"
            : "info",
        message: diag.message,
      });
    }
  }

  return {
    open_files: openFiles,
    recent_edits: [], // Would require document change listener
    diagnostics,
    git_diff: null, // Would require git extension API
    codebase_symbols: [],
  };
}

/**
 * Build a full CopilotContextPayload from the active editor.
 */
export function buildPayload(
  editor: vscode.TextEditor,
  trigger: "keystroke" | "explicit" | "diagnostic",
  maxSuggestions: number = 3
): CopilotContextPayload {
  return {
    cursor: extractCursorContext(editor),
    project: extractProjectContext(),
    trigger,
    max_suggestions: maxSuggestions,
  };
}
