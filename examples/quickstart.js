/**
 * CORTEX Quickstart — JavaScript/TypeScript
 *
 * Usage:
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

  // 3. Ask (RAG)
  console.log("\n🧠 Asking...");
  try {
    const askResp = await fetch(`${BASE_URL}/v1/ask`, {
      method: "POST",
      headers,
      body: JSON.stringify({ query: "What is CORTEX?", k: 5 }),
    });
    const answer = await askResp.json();
    console.log(`  Answer: ${answer.answer}`);
  } catch (e) {
    console.log(`  ⚠️ RAG requires LLM provider: ${e.message}`);
  }

  console.log("\n🎉 CORTEX is operational!");
}

main().catch(console.error);
