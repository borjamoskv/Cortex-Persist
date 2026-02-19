/**
 * CORTEX SDK — Sovereign Memory Engine for Enterprise AI Swarms
 *
 * Zero-dependency TypeScript client for the CORTEX API.
 * Requires Node.js 18+ (native fetch).
 *
 * @example
 * ```typescript
 * import { CortexClient } from '@cortex-memory/sdk';
 *
 * const client = new CortexClient({
 *   baseUrl: 'http://localhost:8000',
 *   apiKey: 'your-api-key',
 * });
 *
 * await client.store({ content: 'Hello CORTEX', project: 'demo' });
 * const results = await client.search('Hello');
 * ```
 */

// ─── Types ──────────────────────────────────────────────────────────

export interface CortexConfig {
  baseUrl: string;
  apiKey?: string;
  tenantId?: string;
  timeout?: number;
}

export interface StoreFact {
  content: string;
  type?: string;
  project?: string;
  tags?: string[];
  meta?: Record<string, unknown>;
}

export interface SearchResult {
  fact_id: number;
  content: string;
  score: number;
  project: string;
  type: string;
}

export interface AskRequest {
  query: string;
  project?: string;
  k?: number;
  temperature?: number;
  max_tokens?: number;
  system_prompt?: string;
}

export interface AskResponse {
  answer: string;
  sources: Array<{
    fact_id: number;
    content: string;
    score: number;
    project: string;
  }>;
  model: string;
  provider: string;
  facts_found: number;
}

export interface HealthResponse {
  status: string;
  version: string;
  facts_count: number;
}

// ─── Client ─────────────────────────────────────────────────────────

export class CortexClient {
  private baseUrl: string;
  private headers: Record<string, string>;
  private timeout: number;

  constructor(config: CortexConfig) {
    this.baseUrl = config.baseUrl.replace(/\/$/, "");
    this.timeout = config.timeout ?? 30000;
    this.headers = {
      "Content-Type": "application/json",
    };
    if (config.apiKey) {
      this.headers["X-API-Key"] = config.apiKey;
    }
    if (config.tenantId) {
      this.headers["X-Tenant-ID"] = config.tenantId;
    }
  }

  private async request<T>(
    method: string,
    path: string,
    body?: unknown
  ): Promise<T> {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeout);

    try {
      const resp = await fetch(`${this.baseUrl}${path}`, {
        method,
        headers: this.headers,
        body: body ? JSON.stringify(body) : undefined,
        signal: controller.signal,
      });

      if (!resp.ok) {
        const error = await resp.text();
        throw new Error(`CORTEX API error ${resp.status}: ${error}`);
      }

      return (await resp.json()) as T;
    } finally {
      clearTimeout(timer);
    }
  }

  async health(): Promise<HealthResponse> {
    return this.request("GET", "/health");
  }

  async store(fact: StoreFact): Promise<{ fact_id: number }> {
    return this.request("POST", "/v1/facts", fact);
  }

  async getFact(id: number): Promise<StoreFact & { fact_id: number }> {
    return this.request("GET", `/v1/facts/${id}`);
  }

  async deleteFact(id: number): Promise<void> {
    await this.request("DELETE", `/v1/facts/${id}`);
  }

  async search(
    query: string,
    options?: { topK?: number; project?: string }
  ): Promise<SearchResult[]> {
    const params = new URLSearchParams({ q: query });
    if (options?.topK) params.set("top_k", String(options.topK));
    if (options?.project) params.set("project", options.project);
    return this.request("GET", `/v1/search?${params}`);
  }

  async ask(request: AskRequest): Promise<AskResponse> {
    return this.request("POST", "/v1/ask", request);
  }

  async listProjects(): Promise<string[]> {
    return this.request("GET", "/v1/projects");
  }
}

export default CortexClient;
