/**
 * CORTEX Copilot — Telemetry Tracker
 *
 * Tracks suggestion lifecycle metrics locally in the VS Code extension.
 * Reports to the CORTEX Copilot output channel.
 */

import * as vscode from "vscode";
import { CopilotTelemetry } from "./types";

export interface TelemetryReport {
  local: LocalTelemetry;
  server: CopilotTelemetry | null;
}

interface LocalTelemetry {
  suggestions_shown: number;
  suggestions_accepted: number;
  suggestions_rejected: number;
  suggestions_expired: number;
  avg_latency_ms: number;
  session_start: number;
  session_duration_ms: number;
}

export class TelemetryTracker {
  private outputChannel: vscode.OutputChannel;
  private suggestionsShown = 0;
  private suggestionsAccepted = 0;
  private suggestionsRejected = 0;
  private suggestionsExpired = 0;
  private latencies: number[] = [];
  private sessionStart: number;
  private serverTelemetry: CopilotTelemetry | null = null;

  constructor() {
    this.outputChannel = vscode.window.createOutputChannel("CORTEX Copilot");
    this.sessionStart = Date.now();
  }

  recordShown(latencyMs: number): void {
    this.suggestionsShown++;
    this.latencies.push(latencyMs);
    this.log(`Suggestion shown (latency: ${latencyMs.toFixed(1)}ms)`);
  }

  recordAccepted(suggestionId: string): void {
    this.suggestionsAccepted++;
    this.log(`✓ Suggestion accepted: ${suggestionId}`);
  }

  recordRejected(suggestionId: string): void {
    this.suggestionsRejected++;
    this.log(`✗ Suggestion rejected: ${suggestionId}`);
  }

  recordExpired(suggestionId: string): void {
    this.suggestionsExpired++;
    this.log(`⏰ Suggestion expired: ${suggestionId}`);
  }

  updateServerTelemetry(telemetry: CopilotTelemetry): void {
    this.serverTelemetry = telemetry;
  }

  getReport(): TelemetryReport {
    const avgLatency =
      this.latencies.length > 0
        ? this.latencies.reduce((a, b) => a + b, 0) / this.latencies.length
        : 0;

    return {
      local: {
        suggestions_shown: this.suggestionsShown,
        suggestions_accepted: this.suggestionsAccepted,
        suggestions_rejected: this.suggestionsRejected,
        suggestions_expired: this.suggestionsExpired,
        avg_latency_ms: avgLatency,
        session_start: this.sessionStart,
        session_duration_ms: Date.now() - this.sessionStart,
      },
      server: this.serverTelemetry,
    };
  }

  showReport(): void {
    const report = this.getReport();
    const l = report.local;
    const total = l.suggestions_accepted + l.suggestions_rejected;
    const rate = total > 0 ? (l.suggestions_accepted / total) * 100 : 0;

    this.outputChannel.clear();
    this.outputChannel.appendLine("╔══════════════════════════════════════╗");
    this.outputChannel.appendLine("║  CORTEX Copilot — Telemetry Report  ║");
    this.outputChannel.appendLine("╠══════════════════════════════════════╣");
    this.outputChannel.appendLine(`║  Suggestions shown:    ${l.suggestions_shown.toString().padStart(8)}`);
    this.outputChannel.appendLine(`║  Accepted:             ${l.suggestions_accepted.toString().padStart(8)}`);
    this.outputChannel.appendLine(`║  Rejected:             ${l.suggestions_rejected.toString().padStart(8)}`);
    this.outputChannel.appendLine(`║  Expired:              ${l.suggestions_expired.toString().padStart(8)}`);
    this.outputChannel.appendLine(`║  Acceptance rate:      ${rate.toFixed(1).padStart(7)}%`);
    this.outputChannel.appendLine(`║  Avg latency:          ${l.avg_latency_ms.toFixed(1).padStart(6)}ms`);
    this.outputChannel.appendLine(`║  Session duration:     ${(l.session_duration_ms / 1000).toFixed(0).padStart(7)}s`);
    this.outputChannel.appendLine("╚══════════════════════════════════════╝");
    this.outputChannel.show();
  }

  dispose(): void {
    this.outputChannel.dispose();
  }

  private log(message: string): void {
    const ts = new Date().toISOString().split("T")[1].slice(0, 12);
    this.outputChannel.appendLine(`[${ts}] ${message}`);
  }
}
