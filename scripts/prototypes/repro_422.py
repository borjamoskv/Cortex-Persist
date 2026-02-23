import json

import requests

import os
BASE_URL = "http://localhost:8000"
KEY = os.environ.get("CORTEX_API_KEY", "your-key-here")  # Loaded from env for security
HEADERS = {"Authorization": f"Bearer {KEY}"}


def check_recall():
    print("--- Recall Project 'test' ---")
    url = f"{BASE_URL}/v1/projects/test/facts"
    resp = requests.get(url, headers=HEADERS)
    print(f"Status: {resp.status_code}")
    if resp.status_code == 422:
        print("Validation Error:")
        print(json.dumps(resp.json(), indent=2))
    else:
        print("Response:")
        try:
            print(json.dumps(resp.json(), indent=2))
        except:
            print(resp.text)


if __name__ == "__main__":
    check_recall()
