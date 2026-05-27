/**
 * CORTEX Copilot — Inline Completion Provider
 *
 * Implements vscode.InlineCompletionItemProvider.
 * This is the core integration point between VS Code's completion API
 * and the CORTEX CopilotAgent backend.
 *
 * Level 3 Contract:
 *   - provideInlineCompletionItems() generates proposals
 *   - Human presses Tab to accept, Escape to dismiss
 *   - The provider NEVER inserts text without human action
 */

import * as vscode from "vscode";
import { CopilotClient } from "./client";
import { buildPayload } from "./context";
import { renderGhostText, renderMultiLineGhost } from "./ghost";
import { TelemetryTracker } from "./telemetry";
import { SuggestionProposal } from "./types";

export class CopilotProvider implements vscode.InlineCompletionItemProvider {
  private client: CopilotClient;
  private telemetry: TelemetryTracker;
  private debounceTimer: ReturnType<typeof setTimeout> | null = null;
  private debounceMs: number;
  private maxSuggestions: number;
  private enabled: boolean;
  private currentSuggestions: SuggestionProposal[] = [];
  private suggestionShownAt = 0;

  constructor(
    client: CopilotClient,
    telemetry: TelemetryTracker,
    options: {
      debounceMs?: number;
      maxSuggestions?: number;
      enabled?: boolean;
    } = {}
  ) {
    this.client = client;
    this.telemetry = telemetry;
    this.debounceMs = options.debounceMs ?? 300;
    this.maxSuggestions = options.maxSuggestions ?? 3;
    this.enabled = options.enabled ?? true;
  }

  async provideInlineCompletionItems(
    document: vscode.TextDocument,
    position: vscode.Position,
    context: vscode.InlineCompletionContext,
    token: vscode.CancellationToken
  ): Promise<vscode.InlineCompletionItem[] | null> {
    if (!this.enabled || !this.client.isConnected) {
      return null;
    }

    // Determine trigger type
    const trigger =
      context.triggerKind === vscode.InlineCompletionTriggerKind.Invoke
        ? "explicit"
        : "keystroke";

    // Get the active editor
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
      return null;
    }

    // Debounce: wait for user to stop typing
    if (this.debounceTimer) {
      clearTimeout(this.debounceTimer);
    }

    return new Promise<vscode.InlineCompletionItem[] | null>((resolve) => {
      this.debounceTimer = setTimeout(async () => {
        // Check if cancelled during debounce
        if (token.isCancellationRequested) {
          resolve(null);
          return;
        }

        try {
          // Build context payload
          const payload = buildPayload(editor, trigger, this.maxSuggestions);

          // Send to backend and receive suggestions
          const t0 = Date.now();
          const batch = await this.client.sendContext(payload);
          const latencyMs = Date.now() - t0;

          this.telemetry.recordShown(latencyMs);

          if (
            !batch.suggestions ||
            batch.suggestions.length === 0 ||
            token.isCancellationRequested
          ) {
            resolve(null);
            return;
          }

          // Store for verdict tracking
          this.currentSuggestions = batch.suggestions;
          this.suggestionShownAt = Date.now();

          // Convert to VS Code InlineCompletionItems
          const items = batch.suggestions
            .filter((s) => s.inline_text)
            .map((s) => renderGhostText(s, position));

          resolve(items.length > 0 ? items : null);
        } catch (error) {
          console.error("[CORTEX Copilot] Provider error:", error);
          resolve(null);
        }
      }, this.debounceMs);
    });
  }

  /**
   * Enable or disable the provider.
   */
  setEnabled(enabled: boolean): void {
    this.enabled = enabled;
  }

  /**
   * Update debounce interval.
   */
  setDebounceMs(ms: number): void {
    this.debounceMs = Math.max(50, ms);
  }

  /**
   * Get current suggestions for verdict tracking.
   */
  getCurrentSuggestions(): SuggestionProposal[] {
    return this.currentSuggestions;
  }

  /**
   * Get the timestamp when current suggestions were shown.
   */
  getSuggestionShownAt(): number {
    return this.suggestionShownAt;
  }
}
