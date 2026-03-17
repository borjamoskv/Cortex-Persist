import { NextResponse } from 'next/server';

const CORTEX_API = process.env.CORTEX_API_URL || 'http://127.0.0.1:8000';

export async function GET() {
  try {
    const res = await fetch(`${CORTEX_API}/health`, {
      headers: { 'Content-Type': 'application/json' },
      signal: AbortSignal.timeout(5000),
    });
    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch {
    return NextResponse.json(
      { status: 'offline', engine: 'unreachable', version: '—', cortisol: 0, neuroplasticity: 0 },
      { status: 503 }
    );
  }
}
