import hmac
import hashlib
import json
import os
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

# Dummy payload reflecting a PR
payload = {
    "action": "opened",
    "pull_request": {
        "number": 42,
        "additions": 150,
        "deletions": 10,
        "changed_files": 3,
        "commits": 2
    },
    "repository": {
        "full_name": "acme-corp/core-api"
    }
}

payload_bytes = json.dumps(payload).encode("utf-8")
secret = os.getenv("GITHUB_WEBHOOK_SECRET", "dev_secret").encode("utf-8")
hash_object = hmac.new(secret, msg=payload_bytes, digestmod=hashlib.sha256)
signature = "sha256=" + hash_object.hexdigest()

headers = {
    "x-github-event": "pull_request",
    "x-hub-signature-256": signature,
    "Content-Type": "application/json"
}

print("=== SIMULATING GITHUB WEBHOOK PAYLOAD ===")
print(f"Target: /api/v1/webhook/github")
print(f"Payload Size: {len(payload_bytes)} bytes")
print(f"Signature: {signature}")

response = client.post("/api/v1/webhook/github", content=payload_bytes, headers=headers)

print("\n=== RESPONSE ===")
print(f"Status Code: {response.status_code}")
print(f"JSON Body: {response.json()}")
