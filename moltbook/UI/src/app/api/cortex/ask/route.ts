import { NextRequest, NextResponse } from 'next/server';

const CORTEX_API = process.env.CORTEX_API_URL || 'http://127.0.0.1:8000';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const res = await fetch(`${CORTEX_API}/v1/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(30000),
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json(
      { detail: 'CORTEX API unreachable — start uvicorn cortex.api.core:app' },
      { status: 503 }
    );
  }
}
