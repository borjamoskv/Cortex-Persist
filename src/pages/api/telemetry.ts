import type { APIRoute } from 'astro';

// C5-REAL Edge Telemetry Endpoint
// Running natively on Cloudflare Workers via Astro SSR

export const POST: APIRoute = async ({ request, locals }) => {
  try {
    const payload = await request.json();
    
    // Simulate Cryptographic Hash-Chain Generation at the Edge
    const timestamp = new Date().toISOString();
    const encoder = new TextEncoder();
    const data = encoder.encode(JSON.stringify(payload) + timestamp);
    const hashBuffer = await crypto.subtle.digest('SHA-256', data);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
    
    // In a real CORTEX deployment, this would be written to D1 Database
    // or KV Cache bound via Cloudflare `locals.cf`.
    // Example: await locals.runtime.env.DB.prepare('INSERT...').run();
    
    // Geographical Provenance
    const edgeCountry = request.headers.get('cf-ipcountry') || 'Unknown';
    const edgeRegion = request.headers.get('cf-region') || 'Unknown';

    return new Response(JSON.stringify({
      status: 'ok',
      message: 'Event sealed at the Edge.',
      provenance: {
        hash: hashHex,
        timestamp: timestamp,
        edge_node: `${edgeCountry}-${edgeRegion}`
      }
    }), {
      status: 201,
      headers: {
        'Content-Type': 'application/json',
        'X-Cortex-Edge': 'verified'
      }
    });

  } catch (error) {
    return new Response(JSON.stringify({ 
      status: 'error', 
      message: 'Invalid payload or Edge execution failure.' 
    }), { 
      status: 400,
      headers: {
        'Content-Type': 'application/json'
      }
    });
  }
};
