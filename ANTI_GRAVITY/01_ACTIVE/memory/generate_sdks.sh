#!/usr/bin/env bash
# [C5-REAL] Exergy-Maximized
# Generate Multi-Language SDKs for CORTEX-Persist

set -e

export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
OPENAPI_FILE="$ROOT_DIR/openapi.json"
SDKS_DIR="$ROOT_DIR/sdks"

echo "Extracting OpenAPI JSON..."
uv run python "$SCRIPT_DIR/extract_openapi.py"

echo "Creating SDKs directory..."
mkdir -p "$SDKS_DIR"

echo "Generating TypeScript SDK..."
mkdir -p "$SDKS_DIR/typescript"
npx @openapitools/openapi-generator-cli generate \
    -i "$OPENAPI_FILE" \
    -g typescript-fetch \
    -o "$SDKS_DIR/typescript" \
    --additional-properties=supportsES6=true,typescriptThreePlus=true,modelPropertyNaming=camelCase

echo "Generating Go SDK..."
mkdir -p "$SDKS_DIR/go"
npx @openapitools/openapi-generator-cli generate \
    -i "$OPENAPI_FILE" \
    -g go \
    -o "$SDKS_DIR/go" \
    --additional-properties=packageName=cortex,isGoSubmodule=true

echo "Generating Rust SDK..."
mkdir -p "$SDKS_DIR/rust"
npx @openapitools/openapi-generator-cli generate \
    -i "$OPENAPI_FILE" \
    -g rust \
    -o "$SDKS_DIR/rust" \
    --additional-properties=packageName=cortex-persist-sdk

echo "✅ All SDKs generated successfully in $SDKS_DIR"
