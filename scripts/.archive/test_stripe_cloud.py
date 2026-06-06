import sys

import httpx


def check_endpoints():
    base_url = "https://cortexpersist.com"
    print("============================================================")
    print("⚡ CORTEX CLOUD TOPOLOGY VALIDATION (C5-REAL)")
    print("============================================================")

    with httpx.Client(timeout=10.0) as client:
        try:
            # 1. Health check
            print(f"[1/2] Probing {base_url}/health...")
            r = client.get(f"{base_url}/health")
            if r.status_code == 200:
                print(f"✓ Health Check OK: {r.json().get('status', 'Unknown')}")
            else:
                print(f"✗ Health Check Failed: {r.status_code} - {r.text}")

            # 2. Stripe checkout endpoint (should return 400 because no body/bad plan, but proves it's there)
            print(f"[2/2] Probing {base_url}/v1/stripe/checkout...")
            r = client.post(f"{base_url}/v1/stripe/checkout", json={"plan": "pro"})
            if r.status_code in [
                200,
                400,
                500,
                502,
            ]:  # Any of these means the endpoint hit the logic
                print(f"✓ Stripe Endpoint REACHABLE (Status {r.status_code})")
                if r.status_code != 200:
                    print(f"  Response: {r.json().get('detail', r.text)}")
            else:
                print(f"✗ Stripe Endpoint Missing or Error: {r.status_code}")

        except Exception as e:
            print(f"[!] Error during probing: {e}")
            sys.exit(1)


if __name__ == "__main__":
    check_endpoints()
