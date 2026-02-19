#!/bin/bash
# CORTEX Docker Quickstart — Run CORTEX in 30 seconds.
#
# Usage:
#   chmod +x docker_quickstart.sh
#   ./docker_quickstart.sh

set -e

echo "🧠 Starting CORTEX..."
docker run -d \
  --name cortex \
  -p 8000:8000 \
  -v cortex-data:/data \
  -e CORTEX_API_KEY=demo-key \
  ghcr.io/borjamoskv/cortex:latest

echo "⏳ Waiting for startup..."
sleep 3

echo "🔍 Health check..."
curl -sf http://localhost:8000/health | python3 -m json.tool

echo ""
echo "📦 Storing a test fact..."
curl -sf -X POST http://localhost:8000/v1/facts \
  -H "Content-Type: application/json" \
  -H "X-API-Key: demo-key" \
  -d '{"content": "CORTEX is a Sovereign Memory Engine for Enterprise AI Swarms.", "type": "knowledge", "project": "demo"}' \
  | python3 -m json.tool

echo ""
echo "🔎 Searching..."
curl -sf "http://localhost:8000/v1/search?q=sovereign+memory&top_k=3" \
  -H "X-API-Key: demo-key" \
  | python3 -m json.tool

echo ""
echo "✅ CORTEX is operational at http://localhost:8000"
echo "📖 API docs: http://localhost:8000/docs"
echo "🛑 Stop: docker stop cortex && docker rm cortex"
