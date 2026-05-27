/**
 * CORTEX Copilot — WebSocket Client
 *
 * Communicates with the Python CopilotServer over WebSocket.
 * Handles connection lifecycle, auto-reconnect, and message correlation.
 */

import {
  CopilotContextPayload,
  SuggestionBatch,
  SuggestionVerdict,
  CopilotTelemetry,
  ServerMessage,
} from "./types";

type ConnectionState = "disconnected" | "connecting" | "connected" | "error";

interface PendingRequest {
  resolve: (batch: SuggestionBatch) => void;
  reject: (error: Error) => void;
  timeout: ReturnType<typeof setTimeout>;
}

export class CopilotClient {
  private ws: WebSocket | null = null;
  private state: ConnectionState = "disconnected";
  private url: string;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000; // ms, exponential backoff
  private pendingRequests = new Map<string, PendingRequest>();
  private requestId = 0;
  private onTelemetryCallback?: (telemetry: CopilotTelemetry) => void;
  private onStateChangeCallback?: (state: ConnectionState) => void;

  constructor(url: string = "ws://localhost:8765") {
    this.url = url;
  }

  get connectionState(): ConnectionState {
    return this.state;
  }

  get isConnected(): boolean {
    return this.state === "connected";
  }

  /**
   * Connect to the CopilotServer.
   */
  async connect(url?: string): Promise<void> {
    if (url) {
      this.url = url;
    }

    this.state = "connecting";
    this.onStateChangeCallback?.(this.state);

    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(this.url);

        this.ws.onopen = () => {
          this.state = "connected";
          this.reconnectAttempts = 0;
          this.onStateChangeCallback?.(this.state);
          resolve();
        };

        this.ws.onmessage = (event: MessageEvent) => {
          this.handleMessage(event.data);
        };

        this.ws.onclose = () => {
          this.state = "disconnected";
          this.onStateChangeCallback?.(this.state);
          this.attemptReconnect();
        };

        this.ws.onerror = (error: Event) => {
          this.state = "error";
          this.onStateChangeCallback?.(this.state);
          reject(new Error("WebSocket connection failed"));
        };
      } catch (error) {
        this.state = "error";
        this.onStateChangeCallback?.(this.state);
        reject(error);
      }
    });
  }

  /**
   * Disconnect from the server.
   */
  disconnect(): void {
    this.maxReconnectAttempts = 0; // Prevent auto-reconnect
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.state = "disconnected";
    this.onStateChangeCallback?.(this.state);

    // Reject all pending requests
    for (const [id, req] of this.pendingRequests) {
      clearTimeout(req.timeout);
      req.reject(new Error("Client disconnected"));
    }
    this.pendingRequests.clear();
  }

  /**
   * Send editor context and receive suggestions.
   * Returns a Promise that resolves with the SuggestionBatch.
   */
  async sendContext(
    payload: CopilotContextPayload,
    timeoutMs: number = 10000
  ): Promise<SuggestionBatch> {
    if (!this.isConnected || !this.ws) {
      throw new Error("Not connected to CopilotServer");
    }

    const id = `req-${++this.requestId}`;

    return new Promise<SuggestionBatch>((resolve, reject) => {
      const timeout = setTimeout(() => {
        this.pendingRequests.delete(id);
        reject(new Error(`Request ${id} timed out after ${timeoutMs}ms`));
      }, timeoutMs);

      this.pendingRequests.set(id, { resolve, reject, timeout });

      this.ws!.send(
        JSON.stringify({
          type: "context",
          payload,
          _request_id: id,
        })
      );
    });
  }

  /**
   * Send human verdict on a suggestion.
   * Fire-and-forget — no response expected.
   */
  sendVerdict(verdict: SuggestionVerdict): void {
    if (!this.isConnected || !this.ws) {
      return;
    }

    this.ws.send(
      JSON.stringify({
        type: "verdict",
        payload: verdict,
      })
    );
  }

  /**
   * Register telemetry update callback.
   */
  onTelemetry(callback: (telemetry: CopilotTelemetry) => void): void {
    this.onTelemetryCallback = callback;
  }

  /**
   * Register connection state change callback.
   */
  onStateChange(callback: (state: ConnectionState) => void): void {
    this.onStateChangeCallback = callback;
  }

  // ── Internal ──────────────────────────────────────────────────

  private handleMessage(raw: string): void {
    try {
      const msg: ServerMessage = JSON.parse(raw);

      switch (msg.type) {
        case "suggestions":
          // Resolve the oldest pending request
          const [firstId] = this.pendingRequests.keys();
          if (firstId) {
            const req = this.pendingRequests.get(firstId)!;
            clearTimeout(req.timeout);
            this.pendingRequests.delete(firstId);
            req.resolve(msg.payload);
          }
          break;

        case "telemetry":
          this.onTelemetryCallback?.(msg.payload);
          break;

        case "error":
          console.error("[CORTEX Copilot] Server error:", msg.message);
          break;

        case "health":
          // Health check response — no action needed
          break;
      }
    } catch (error) {
      console.error("[CORTEX Copilot] Failed to parse message:", error);
    }
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      return;
    }

    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);

    setTimeout(async () => {
      try {
        await this.connect();
      } catch {
        // Will retry via onclose handler
      }
    }, delay);
  }
}
