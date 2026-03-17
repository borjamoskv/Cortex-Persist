import { NextRequest } from 'next/server';

const CORTEX_API = process.env.CORTEX_API_URL || 'http://127.0.0.1:8000';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const res = await fetch(`${CORTEX_API}/v1/ask/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(60000),
    });

    if (!res.ok || !res.body) {
      const data = await res.json().catch(() => ({ detail: 'LLM unavailable' }));
      return new Response(JSON.stringify(data), {
        status: res.status,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    // Forward SSE stream directly
    return new Response(res.body, {
      status: 200,
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        Connection: 'keep-alive',
      },
    });
  } catch {
    return new Response(
      JSON.stringify({ detail: 'CORTEX API unreachable — start uvicorn cortex.api.core:app' }),
      { status: 503, headers: { 'Content-Type': 'application/json' } }
    );
  }
}
