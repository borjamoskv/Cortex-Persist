import json
import subprocess
import sys

API_KEY = "moltbook_sk_UW38_ewFWR5OFB-CnIpfiKiucSmpFsSu"
# Article text:
with open('/Users/borjafernandezangulo/30_CORTEX/naroa-2026/docs/wikipedia/wikipedia_naroa_input_v3.txt', 'r', encoding='utf-8') as f:
    content = f.read()

payload_dict = {
    "submolt_name": "webdev",
    "title": "Naroa Gutiérrez Gil - Wikipedia Draft",
    "content": content
}
payload_bytes = json.dumps(payload_dict).encode('utf-8')

print("Posting to Moltbook via curl...")
result = subprocess.run([
    'curl', '-X', 'POST', 'https://www.moltbook.com/api/v1/posts',
    '-H', f'Authorization: Bearer {API_KEY}',
    '-H', 'Content-Type: application/json',
    '-d', '@-'
], input=payload_bytes, capture_output=True)

print("Status:", result.returncode)
try:
    print(json.dumps(json.loads(result.stdout.decode('utf-8')), indent=2))
except Exception:
    print(result.stdout.decode('utf-8'))

if result.stderr:
    print("Stderr:", result.stderr.decode('utf-8'))
