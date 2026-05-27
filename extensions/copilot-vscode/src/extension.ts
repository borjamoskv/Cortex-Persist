/**
 * CORTEX Copilot — VS Code Extension Entry Point
 *
 * ██████╗ ██████╗ ██████╗ ██╗██╗      ██████╗ ████████╗
 * ██╔════╝██╔═══██╗██╔══██╗██║██║     ██╔═══██╗╚══██╔══╝
 * ██║     ██║   ██║██████╔╝██║██║     ██║   ██║   ██║
 * ██║     ██║   ██║██╔═══╝ ██║██║     ██║   ██║   ██║
 * ╚██████╗╚██████╔╝██║     ██║███████╗╚██████╔╝   ██║
 *  ╚═════╝ ╚═════╝ ╚═╝     ╚═╝╚══════╝ ╚═════╝    ╚═╝
 *
 * LEVEL 3 — COPILOT
 * Suggests actions inline. The human accepts/rejects. Never acts alone.
 */

import * as vscode from "vscode";
import { CopilotClient } from "./client";
import { CopilotProvider } from "./provider";
import { TelemetryTracker } from "./telemetry";
import { createAcceptVerdict, createRejectVerdict } from "./ghost";
import { SuggestionStatus } from "./types";

let client: CopilotClient;
let provider: CopilotProvider;
let telemetry: TelemetryTracker;
let statusBarItem: vscode.StatusBarItem;

export function activate(context: vscode.ExtensionContext): void {
  // ── Initialize components ──────────────────────────────────────
  const config = vscode.workspace.getConfiguration("cortex-copilot");
  const serverUrl = config.get<string>("serverUrl", "ws://localhost:8765");
  const debounceMs = config.get<number>("debounceMs", 300);
  const maxSuggestions = config.get<number>("maxSuggestions", 3);
  const enabled = config.get<boolean>("enabled", true);

  client = new CopilotClient(serverUrl);
  telemetry = new TelemetryTracker();
  provider = new CopilotProvider(client, telemetry, {
    debounceMs,
    maxSuggestions,
    enabled,
  });

  // ── Register inline completion provider ────────────────────────
  const providerDisposable = vscode.languages.registerInlineCompletionItemProvider(
    { pattern: "**" }, // All languages
    provider
  );
  context.subscriptions.push(providerDisposable);

  // ── Status bar ─────────────────────────────────────────────────
  statusBarItem = vscode.window.createStatusBarItem(
    vscode.StatusBarAlignment.Right,
    100
  );
  statusBarItem.command = "cortex-copilot.showTelemetry";
  updateStatusBar("disconnected");
  statusBarItem.show();
  context.subscriptions.push(statusBarItem);

  // ── Connection state tracking ──────────────────────────────────
  client.onStateChange((state) => {
    updateStatusBar(state);
  });

  client.onTelemetry((serverTelemetry) => {
    telemetry.updateServerTelemetry(serverTelemetry);
  });

  // ── Commands ───────────────────────────────────────────────────
  context.subscriptions.push(
    vscode.commands.registerCommand("cortex-copilot.enable", () => {
      provider.setEnabled(true);
      updateStatusBar(client.connectionState);
      vscode.window.showInformationMessage("CORTEX Copilot enabled");
    }),

    vscode.commands.registerCommand("cortex-copilot.disable", () => {
      provider.setEnabled(false);
      updateStatusBar("disabled");
      vscode.window.showInformationMessage("CORTEX Copilot disabled");
    }),

    vscode.commands.registerCommand("cortex-copilot.showTelemetry", () => {
      telemetry.showReport();
    }),

    vscode.commands.registerCommand(
      "cortex-copilot.acceptSuggestion",
      (suggestionId: string) => {
        const verdict = createAcceptVerdict(
          suggestionId,
          provider.getSuggestionShownAt()
        );
        client.sendVerdict(verdict);
        telemetry.recordAccepted(suggestionId);
      }
    ),

    vscode.commands.registerCommand(
      "cortex-copilot.rejectSuggestion",
      (suggestionId: string) => {
        const verdict = createRejectVerdict(
          suggestionId,
          provider.getSuggestionShownAt()
        );
        client.sendVerdict(verdict);
        telemetry.recordRejected(suggestionId);
      }
    )
  );

  // ── Auto-connect ───────────────────────────────────────────────
  if (enabled) {
    client.connect().catch((error) => {
      console.warn("[CORTEX Copilot] Initial connection failed:", error);
      updateStatusBar("error");
    });
  }

  // ── Configuration change listener ──────────────────────────────
  context.subscriptions.push(
    vscode.workspace.onDidChangeConfiguration((e) => {
      if (e.affectsConfiguration("cortex-copilot")) {
        const newConfig = vscode.workspace.getConfiguration("cortex-copilot");
        provider.setDebounceMs(newConfig.get<number>("debounceMs", 300));
        provider.setEnabled(newConfig.get<boolean>("enabled", true));
      }
    })
  );

  // Activated
}

export function deactivate(): void {
  client?.disconnect();
  telemetry?.dispose();
  statusBarItem?.dispose();
  // Deactivated
}

// ── Status Bar Helper ────────────────────────────────────────────

function updateStatusBar(
  state: "disconnected" | "connecting" | "connected" | "error" | "disabled"
): void {
  switch (state) {
    case "connected":
      statusBarItem.text = "$(copilot) CORTEX";
      statusBarItem.tooltip = "CORTEX Copilot — Connected";
      statusBarItem.backgroundColor = undefined;
      break;
    case "connecting":
      statusBarItem.text = "$(sync~spin) CORTEX";
      statusBarItem.tooltip = "CORTEX Copilot — Connecting...";
      break;
    case "disconnected":
      statusBarItem.text = "$(circle-slash) CORTEX";
      statusBarItem.tooltip = "CORTEX Copilot — Disconnected";
      break;
    case "error":
      statusBarItem.text = "$(error) CORTEX";
      statusBarItem.tooltip = "CORTEX Copilot — Connection Error";
      statusBarItem.backgroundColor = new vscode.ThemeColor(
        "statusBarItem.errorBackground"
      );
      break;
    case "disabled":
      statusBarItem.text = "$(circle-slash) CORTEX Off";
      statusBarItem.tooltip = "CORTEX Copilot — Disabled";
      break;
  }
}
