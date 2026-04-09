/**
 * CORTEX Quickstart — JavaScript/TypeScript against the self-hosted beta API.
 *
 * Usage:
 *   git clone https://github.com/borjamoskv/Cortex-Persist.git
 *   cd Cortex-Persist
 *   pip install -e ".[api]"
 *   uvicorn cortex.api:app --port 8000
 *   node quickstart.js
 *
 * No dependencies required — uses native fetch (Node 18+).
 */

const BASE_URL = "http://localhost:8000";
const API_KEY = "<YOUR_API_KEY>";

const headers = {
  "Content-Type": "application/json",
  "X-API-Key": API_KEY,
};

async function main() {
  // 1. Store a fact
  console.log("📦 Storing fact...");
  const storeResp = await fetch(`${BASE_URL}/v1/facts`, {
    method: "POST",
    headers,
    body: JSON.stringify({
      content:
        "CORTEX is a Sovereign Memory Engine for Enterprise AI Swarms.",
      type: "knowledge",
      project: "demo",
    }),
  });
  const stored = await storeResp.json();
  console.log(`  ✅ Stored fact #${stored.fact_id}`);

  // 2. Search
  console.log("\n🔎 Searching...");
  const searchResp = await fetch(
    `${BASE_URL}/v1/search?q=sovereign+memory&top_k=3`,
    { headers }
  );
  const results = await searchResp.json();
  for (const r of results.results || results) {
    console.log(`  [#${r.fact_id}] (score: ${r.score?.toFixed(3)}) ${r.content?.slice(0, 80)}`);
  }

  // 3. Recall project facts
  console.log("\n📚 Recalling project facts...");
  const recallResp = await fetch(`${BASE_URL}/v1/projects/demo/facts`, { headers });
  const facts = await recallResp.json();
  console.log(`  ✅ Recalled ${facts.length} fact(s)`);

  // 4. Check engine status
  console.log("\n🩺 Checking status...");
  const statusResp = await fetch(`${BASE_URL}/v1/status`, { headers });
  const status = await statusResp.json();
  console.log(`  Status: ${JSON.stringify(status)}`);

  console.log("\n🎉 CORTEX is operational!");
}

main().catch(console.error);
